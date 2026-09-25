"""Tests for labels, entity IDs, unique_ids and legacy default IDs."""
from custom_components.bitpanda.naming import (
    LEGACY_PORTFOLIO_OBJECT_ID,
    asset_display_label,
    asset_slug,
    is_default_entity_id,
    legacy_price_object_id,
    legacy_wallet_object_id,
    managed_asset_id,
    portfolio_device_identifier,
    portfolio_entity_id,
    portfolio_unique_id,
    price_device_identifier,
    price_entity_id,
    price_unique_id,
    price_unique_id_currency,
    return_key,
    staking_entity_id,
    staking_unique_id,
    total_entity_id,
    total_unique_id,
    wallet_device_identifier,
    wallet_entity_id,
    wallet_unique_id,
)

BTC = {"id": "b86c034b-efe3-11eb-b56f-0691764446a7", "symbol": "BTC", "name": "Bitcoin"}
BNB = {"id": "b86cb91a-efe3-11eb-b56f-0691764446a7", "symbol": "BNB", "name": "BNB"}
BCI5 = {"id": "b86ca64c-efe3-11eb-b56f-0691764446a7", "symbol": "BCI5", "name": "BCI 5"}
GOLD = {"id": "b86c88d4-efe3-11eb-b56f-0691764446a7", "symbol": "XAU", "name": "Gold"}
GOLDMONEY = {
    "id": "1f0f13b5-0c40-638c-a180-6ba272521ad2",
    "symbol": "XAU",
    "name": "GoldMoney Inc",
}
VISION = {"id": "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb", "symbol": "VSN", "name": "Vision"}


def test_label_is_name_and_symbol():
    assert asset_display_label(BTC) == "Bitcoin (BTC)"
    assert asset_display_label(GOLDMONEY) == "GoldMoney Inc (XAU)"


def test_label_is_the_symbol_when_the_name_only_repeats_it():
    """Compared ignoring case and spaces: "BCI 5" is BCI5, "BNB" is BNB."""
    assert asset_display_label(BNB) == "BNB"
    assert asset_display_label(BCI5) == "BCI5"


def test_label_without_a_name_is_the_symbol():
    assert asset_display_label({"id": "x", "symbol": "ABC", "name": None}) == "ABC"
    assert asset_display_label({"id": "x", "symbol": "ABC"}) == "ABC"


def test_slug():
    assert asset_slug(VISION) == "vision_vsn"
    assert asset_slug(GOLDMONEY) == "goldmoney_inc_xau"


def test_entity_ids_match_the_spec_table():
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
    assert wallet_entity_id(VISION) == "sensor.bitpanda_vision_vsn_wallet"
    assert staking_entity_id(VISION) == "sensor.bitpanda_vision_vsn_wallet_staking"
    assert total_entity_id(VISION) == "sensor.bitpanda_vision_vsn_wallet_total"
    assert wallet_entity_id(GOLD) == "sensor.bitpanda_gold_xau_wallet"
    assert wallet_entity_id(BCI5) == "sensor.bitpanda_bci5_wallet"
    assert price_entity_id(BTC, "EUR") == "sensor.bitpanda_bitcoin_btc_eur"
    assert price_entity_id(BTC, "USD") == "sensor.bitpanda_bitcoin_btc_usd"
    assert price_entity_id(GOLDMONEY, "EUR") == "sensor.bitpanda_goldmoney_inc_xau_eur"


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


def test_price_unique_id_currency():
    asset_id = BTC["id"]
    assert price_unique_id_currency("eid", f"eid_{asset_id}_price_USD") == "USD"
    assert price_unique_id_currency("other", f"eid_{asset_id}_price_USD") is None
    # A legacy price unique_id carries a symbol, not a UUID.
    assert price_unique_id_currency("eid", "eid_BTC_price_EUR") is None


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
