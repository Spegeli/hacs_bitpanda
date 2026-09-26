"""Tests for labels, entity IDs, unique_ids and legacy default IDs."""
from custom_components.bitpanda.naming import (
    LEGACY_PORTFOLIO_OBJECT_ID,
    asset_display_label,
    is_default_entity_id,
    legacy_price_object_id,
    legacy_wallet_object_id,
    managed_asset_id,
    managed_asset_key,
    portfolio_device_identifier,
    portfolio_entity_id,
    portfolio_unique_id,
    price_device_asset_id,
    price_device_identifier,
    price_device_name,
    price_entity_id,
    price_key,
    price_unique_id,
    return_key,
    staking_entity_id,
    staking_unique_id,
    total_entity_id,
    total_unique_id,
    wallet_device_asset_id,
    wallet_device_identifier,
    wallet_device_name,
    wallet_entity_id,
    wallet_unique_id,
)

BTC = {"id": "b86c034b-efe3-11eb-b56f-0691764446a7", "symbol": "BTC", "name": "Bitcoin"}
BNB = {"id": "b86cb91a-efe3-11eb-b56f-0691764446a7", "symbol": "BNB", "name": "BNB"}
BCI5 = {"id": "b86ca64c-efe3-11eb-b56f-0691764446a7", "symbol": "BCI5", "name": "BCI 5"}
GOLD = {"id": "b86c88d4-efe3-11eb-b56f-0691764446a7", "symbol": "XAU", "name": "Gold",
        "type": "commodity", "group": "metal"}
GOLDMONEY = {
    "id": "1f0f13b5-0c40-638c-a180-6ba272521ad2",
    "symbol": "XAU",
    "name": "GoldMoney Inc",
    "isin": "VGG4001R1047",
    "type": "equity_security",
    "group": "equity_stock",
}
VISION = {"id": "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb", "symbol": "VSN", "name": "Vision"}
# An ETF, and a stock whose name only repeats its symbol (as ~110 do).
AMUNDI = {
    "id": "1f0ed6c9-ee10-68c6-8a0e-55a29b7757fe",
    "symbol": "LYY1",
    "name": "Amundi PEA S&P 500 UCITS ETF",
    "isin": "FR0011871136",
    "type": "equity_security",
    "group": "equity_etf",
}
GRAB = {
    "id": "04717cf5-b0f4-11ec-a6ac-0a686dc2c129",
    "symbol": "GRAB",
    "name": "Grab",
    "isin": "KYG4124C1096",
    "type": "security",
    "group": "stock",
}
CASH_PLUS = {
    "id": "1edf9721-e545-644c-9796-ae5b69a774d7",
    "symbol": "BCPEUR",
    "name": "Bitpanda Cash Plus EUR",
    "isin": "IE000GWTNRJ7",
    "type": "security",
    "group": "fiat_earn",
}


def test_label_is_name_and_symbol():
    assert asset_display_label(BTC) == "Bitcoin (BTC)"
    assert asset_display_label(GOLD) == "Gold (XAU)"


def test_label_is_the_symbol_when_the_name_only_repeats_it():
    """Compared ignoring case and spaces: "BCI 5" is BCI5, "BNB" is BNB."""
    assert asset_display_label(BNB) == "BNB"
    assert asset_display_label(BCI5) == "BCI5"


def test_label_without_a_name_is_the_symbol():
    assert asset_display_label({"id": "x", "symbol": "ABC", "name": None}) == "ABC"
    assert asset_display_label({"id": "x", "symbol": "ABC"}) == "ABC"


def test_a_stock_etf_or_etc_label_carries_its_isin():
    """Name, symbol and ISIN: GoldMoney's stock no longer reads like a metal."""
    assert asset_display_label(AMUNDI) == "Amundi PEA S&P 500 UCITS ETF (LYY1 / FR0011871136)"
    assert asset_display_label(GOLDMONEY) == "GoldMoney Inc (XAU / VGG4001R1047)"


def test_a_security_whose_name_only_repeats_its_symbol_is_symbol_and_isin():
    assert asset_display_label(GRAB) == "GRAB (KYG4124C1096)"
    assert asset_display_label({**GRAB, "name": None}) == "GRAB (KYG4124C1096)"


def test_any_other_label_leaves_the_isin_out():
    """Cash Plus has an ISIN, but is no stock, ETF or ETC; a stock without
    an ISIN has none to show."""
    assert asset_display_label(CASH_PLUS) == "Bitpanda Cash Plus EUR (BCPEUR)"
    assert asset_display_label({**AMUNDI, "isin": None}) == "Amundi PEA S&P 500 UCITS ETF (LYY1)"


def test_device_names_say_what_the_device_is_in_english():
    """Home Assistant lists an entity under its device's name, so the name
    tells a price sensor from a wallet's in every language."""
    assert wallet_device_name(VISION) == "Vision (VSN) Wallet"
    assert price_device_name(VISION) == "Vision (VSN) Price Tracker"
    assert price_device_name(BNB) == "BNB Price Tracker"
    assert (
        price_device_name(AMUNDI)
        == "Amundi PEA S&P 500 UCITS ETF (LYY1 / FR0011871136) Price Tracker"
    )
    assert wallet_device_name(GRAB) == "GRAB (KYG4124C1096) Wallet"


def test_entity_ids_match_the_spec_table():
    """sensor.bitpanda_ + the slug of the device's name + the sensor's own
    ending, in both services: the Portfolio device is "Portfolio"."""
    assert portfolio_entity_id("total") == "sensor.bitpanda_portfolio_total"
    assert portfolio_entity_id("cash") == "sensor.bitpanda_portfolio_cash"
    assert portfolio_entity_id("cash_plus") == "sensor.bitpanda_portfolio_cash_plus"
    assert portfolio_entity_id(return_key("DAY")) == "sensor.bitpanda_portfolio_return_day"
    assert portfolio_entity_id(return_key("WEEK")) == "sensor.bitpanda_portfolio_return_week"
    assert (
        portfolio_entity_id(return_key("MONTH"))
        == "sensor.bitpanda_portfolio_return_month"
    )
    assert (
        portfolio_entity_id(return_key("SIX_MONTH"))
        == "sensor.bitpanda_portfolio_return_6_months"
    )
    assert portfolio_entity_id(return_key("YEAR")) == "sensor.bitpanda_portfolio_return_year"
    # The wallet sensor ends in its name, "Balance (available)", like its
    # siblings: `…_wallet` alone would read as the whole wallet.
    assert wallet_entity_id(VISION) == "sensor.bitpanda_vision_vsn_wallet_available"
    assert staking_entity_id(VISION) == "sensor.bitpanda_vision_vsn_wallet_staking"
    assert total_entity_id(VISION) == "sensor.bitpanda_vision_vsn_wallet_total"
    assert wallet_entity_id(GOLD) == "sensor.bitpanda_gold_xau_wallet_available"
    assert wallet_entity_id(BCI5) == "sensor.bitpanda_bci5_wallet_available"
    assert price_entity_id(VISION, "EUR") == "sensor.bitpanda_vision_vsn_price_tracker_eur"
    assert price_entity_id(BTC, "EUR") == "sensor.bitpanda_bitcoin_btc_price_tracker_eur"
    assert price_entity_id(BTC, "USD") == "sensor.bitpanda_bitcoin_btc_price_tracker_usd"
    assert price_entity_id(BNB, "CHF") == "sensor.bitpanda_bnb_price_tracker_chf"
    # A stock's, ETF's or ETC's ISIN is part of its label, so of its IDs.
    assert (
        price_entity_id(AMUNDI, "CHF")
        == "sensor.bitpanda_amundi_pea_s_p_500_ucits_etf_lyy1_fr0011871136_price_tracker_chf"
    )
    assert (
        wallet_entity_id(AMUNDI)
        == "sensor.bitpanda_amundi_pea_s_p_500_ucits_etf_lyy1_fr0011871136_wallet_available"
    )
    assert (
        price_entity_id(GOLDMONEY, "EUR")
        == "sensor.bitpanda_goldmoney_inc_xau_vgg4001r1047_price_tracker_eur"
    )
    assert price_entity_id(GRAB, "EUR") == "sensor.bitpanda_grab_kyg4124c1096_price_tracker_eur"


def test_unique_ids_and_device_identifiers():
    asset_id = VISION["id"]
    assert portfolio_unique_id("eid", "total") == "eid_portfolio_total"
    assert portfolio_unique_id("eid", return_key("SIX_MONTH")) == "eid_portfolio_return_six_month"
    assert wallet_unique_id("eid", asset_id) == f"eid_wallet_{asset_id}"
    assert staking_unique_id("eid", asset_id) == f"eid_staking_{asset_id}"
    assert total_unique_id("eid", asset_id) == f"eid_total_{asset_id}"
    assert price_unique_id("eid", asset_id, "USD") == f"eid_{asset_id}_price_USD"
    assert portfolio_device_identifier("eid") == "eid_portfolio"
    assert wallet_device_identifier("eid", asset_id) == f"eid_wallet_{asset_id}"
    assert price_device_identifier("eid", asset_id) == f"eid_price_{asset_id}"


def test_managed_asset_id_reads_only_uuid_suffixes_of_this_entry():
    asset_id = VISION["id"]
    assert managed_asset_id("eid", f"eid_wallet_{asset_id}") == asset_id
    assert managed_asset_id("eid", f"eid_staking_{asset_id}") == asset_id
    assert managed_asset_id("eid", f"eid_total_{asset_id}") == asset_id
    # A legacy wallet the migration could not resolve keeps its old id and
    # must never be mistaken for a managed wallet.
    assert managed_asset_id("eid", "eid_wallet_cryptocoin_BTC") is None
    assert managed_asset_id("eid", "eid_portfolio_total") is None
    assert managed_asset_id("eid", f"other_wallet_{asset_id}") is None


def test_managed_asset_key_reads_the_kind_as_well():
    asset_id = VISION["id"]
    assert managed_asset_key("eid", wallet_unique_id("eid", asset_id)) == ("wallet", asset_id)
    assert managed_asset_key("eid", staking_unique_id("eid", asset_id)) == ("staking", asset_id)
    assert managed_asset_key("eid", total_unique_id("eid", asset_id)) == ("total", asset_id)
    assert managed_asset_key("eid", "eid_wallet_cryptocoin_BTC") is None
    assert managed_asset_key("eid", portfolio_unique_id("eid", "total")) is None


def test_price_key_reads_asset_and_currency_of_this_entry():
    asset_id = BTC["id"]
    assert price_key("eid", price_unique_id("eid", asset_id, "USD")) == (asset_id, "USD")
    assert price_key("other", f"eid_{asset_id}_price_USD") is None
    # A legacy price unique_id carries a symbol, not a UUID.
    assert price_key("eid", "eid_BTC_price_EUR") is None
    assert price_key("eid", f"eid_{asset_id}_price_") is None
    assert price_key("eid", wallet_unique_id("eid", asset_id)) is None


def test_price_device_asset_id_reads_only_price_devices_of_this_entry():
    asset_id = BTC["id"]
    assert price_device_asset_id("eid", price_device_identifier("eid", asset_id)) == asset_id
    assert price_device_asset_id("other", price_device_identifier("eid", asset_id)) is None
    assert price_device_asset_id("eid", wallet_device_identifier("eid", asset_id)) is None
    # The legacy "Bitpanda Price Tracker" device.
    assert price_device_asset_id("eid", "eid_price_tracker") is None


def test_wallet_device_asset_id_reads_only_wallet_devices_of_this_entry():
    asset_id = VISION["id"]
    assert wallet_device_asset_id("eid", wallet_device_identifier("eid", asset_id)) == asset_id
    assert wallet_device_asset_id("other", wallet_device_identifier("eid", asset_id)) is None
    assert wallet_device_asset_id("eid", price_device_identifier("eid", asset_id)) is None
    assert wallet_device_asset_id("eid", portfolio_device_identifier("eid")) is None
    # The legacy "Bitpanda Wallets" device.
    assert wallet_device_asset_id("eid", "eid_wallets") is None


def test_legacy_default_object_ids():
    """Legacy entities had has_entity_name=True on the devices "Bitpanda
    Price Tracker" and "Bitpanda Wallets", named "BTC/EUR", "VSN Wallet" and
    "Portfolio Total"."""
    assert legacy_price_object_id("BTC", "EUR") == "bitpanda_price_tracker_btc_eur"
    assert legacy_wallet_object_id("VSN") == "bitpanda_wallets_vsn_wallet"
    assert legacy_wallet_object_id("EUR") == "bitpanda_wallets_eur_wallet"
    assert LEGACY_PORTFOLIO_OBJECT_ID == "bitpanda_wallets_portfolio_total"


def test_default_entity_id_allows_a_numeric_suffix_only():
    object_id = "bitpanda_wallets_vsn_wallet"
    assert is_default_entity_id("sensor.bitpanda_wallets_vsn_wallet", object_id)
    assert is_default_entity_id("sensor.bitpanda_wallets_vsn_wallet_2", object_id)
    assert is_default_entity_id("sensor.bitpanda_wallets_vsn_wallet_12", object_id)
    assert not is_default_entity_id("sensor.my_vision", object_id)
    assert not is_default_entity_id("sensor.bitpanda_wallets_vsn_wallet_old", object_id)
