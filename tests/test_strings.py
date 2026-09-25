"""The three string files stay structurally identical and BOM-free."""
import json
from pathlib import Path

from custom_components.bitpanda.assets import ASSET_CATEGORY_FILTERS, CATEGORY_OTHER
from custom_components.bitpanda.ecb import EcbRates
from custom_components.bitpanda.portfolio_model import (
    EarnData,
    Holding,
    PortfolioData,
    RewardTotals,
)
from custom_components.bitpanda.portfolio_sensor import (
    PortfolioCashPlusSensor,
    StakingSensor,
    WalletSensor,
    WalletTotalSensor,
)
from custom_components.bitpanda.price_sensor import PriceSensor

_DIR = Path(__file__).parent.parent / "custom_components" / "bitpanda"
_FILES = ("strings.json", "translations/en.json", "translations/de.json")


def _paths(node, prefix: str = "") -> set[str]:
    if not isinstance(node, dict):
        return set()
    out: set[str] = set()
    for key, value in node.items():
        out.add(prefix + key)
        out |= _paths(value, f"{prefix}{key}.")
    return out


def test_string_files_have_no_bom():
    for name in _FILES:
        assert not (_DIR / name).read_bytes().startswith(b"\xef\xbb\xbf"), name


def test_string_files_share_one_structure():
    structures = [
        _paths(json.loads((_DIR / name).read_text(encoding="utf-8"))) for name in _FILES
    ]
    assert structures[0] == structures[1] == structures[2]


def test_english_translation_is_the_strings_file():
    strings = json.loads((_DIR / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((_DIR / "translations/en.json").read_text(encoding="utf-8"))
    assert strings == english


def test_every_currency_and_entity_name_is_translated():
    strings = json.loads((_DIR / "strings.json").read_text(encoding="utf-8"))
    # Lowercase: hassfest's translation-key validator rejects uppercase
    # selector option keys (see config_flow.py's _currency_select).
    assert set(strings["selector"]["currency"]["options"]) == {
        "chf", "czk", "dkk", "eur", "gbp", "huf", "nok", "pln", "ron", "sek", "try", "usd",
    }
    assert set(strings["entity"]["sensor"]) == {
        "total_value", "cash", "cash_plus", "return_day", "return_week",
        "return_month", "return_six_month", "return_year", "staking", "wallet_total",
        "wallet", "price",
    }


def test_the_price_group_flow_has_its_strings():
    strings = json.loads((_DIR / "strings.json").read_text(encoding="utf-8"))
    assert set(strings["config_subentries"]) == {"price_group", "wallet_group"}
    group = strings["config_subentries"]["price_group"]
    assert set(group["step"]) == {"user", "asset"}
    assert set(group["abort"]) == {"already_configured", "asset_added"}
    assert "{asset}" in group["abort"]["asset_added"]
    assert "{group}" in group["abort"]["asset_added"]


def test_the_wallet_group_is_named_and_has_no_flow():
    """No dialog ever adds a wallet group, yet hassfest wants the strings of
    a flow: `initiate_flow.user` and a `step` block, here empty."""
    english, german = (
        json.loads((_DIR / name).read_text(encoding="utf-8"))["config_subentries"]["wallet_group"]
        for name in ("strings.json", "translations/de.json")
    )
    assert english == {
        "initiate_flow": {"user": "Add wallet group"},
        "entry_type": "Wallet group",
        "step": {},
    }
    assert german == {
        "initiate_flow": {"user": "Wallet-Gruppe hinzufügen"},
        "entry_type": "Wallet-Gruppe",
        "step": {},
    }


def test_cash_plus_attribute_names_show_the_currency_code():
    """So the frontend shows `EUR`, not a title-cased key (`Eur`); identical
    in every language, since a currency code is never translated."""
    expected = {
        "eur": {"name": "EUR"},
        "usd": {"name": "USD"},
        "gbp": {"name": "GBP"},
    }
    for name in _FILES:
        strings = json.loads((_DIR / name).read_text(encoding="utf-8"))
        assert strings["entity"]["sensor"]["cash_plus"]["state_attributes"] == expected, name


def test_every_asset_category_has_a_group_title():
    strings = json.loads((_DIR / "strings.json").read_text(encoding="utf-8"))
    assert set(strings["selector"]["asset_group"]["options"]) == {
        *ASSET_CATEGORY_FILTERS, CATEGORY_OTHER,
    }


# --- Attribute label drift guard --------------------------------------------------
#
# Every attribute a sensor can publish must have a translated label under its
# translation_key: Home Assistant's more-info "Details" view sorts attributes
# alphabetically by their displayed label, mixed with its own (device class,
# friendly name, ...), and only a translation lets an integration control that
# label at all (see the sensor modules' docstrings). Each scenario below is
# built to make one sensor class publish every attribute it can, so a new
# attribute added without a matching label here fails this test.


class _Coordinator:
    """Duck-typed coordinator: what the entities read."""

    def __init__(self, data=None, last_update_success=True):
        self.data = data
        self.last_update_success = last_update_success


_VSN = {"id": "1f051b7c-5980-6dda-9d3d-cf107d8d4bfb", "symbol": "VSN", "name": "Vision",
        "group": "token"}
_BCPEUR = {"id": "cash-plus-eur", "symbol": "BCPEUR", "name": "Bitpanda Cash Plus EUR",
           "group": "fiat_earn"}
_BCPUSD = {"id": "cash-plus-usd", "symbol": "BCPUSD", "name": "Bitpanda Cash Plus USD",
           "group": "fiat_earn"}
_BCPGBP = {"id": "cash-plus-gbp", "symbol": "BCPGBP", "name": "Bitpanda Cash Plus GBP",
           "group": "fiat_earn"}
_BTC = {"id": "b86c034b-efe3-11eb-b56f-0691764446a7", "symbol": "BTC", "name": "Bitcoin",
        "group": "coin"}


def _wallet_portfolio_data() -> PortfolioData:
    """One holding with every performance figure set, so WalletSensor and
    WalletTotalSensor both publish the full performance set."""
    holding = Holding(
        asset_id=_VSN["id"], balance=100.0, available=25.0, value=200.0,
        invested=150.0, avg_buy_price=1.5, total_return=50.0, total_return_pct=33.33,
    )
    data = PortfolioData(holdings={_VSN["id"]: holding}, cash=0.0)
    data.assets = {_VSN["id"]: _VSN}
    return data


def _cash_plus_portfolio_data() -> PortfolioData:
    """A Cash Plus holding in each of the three known product currencies."""
    products = (_BCPEUR, _BCPUSD, _BCPGBP)
    data = PortfolioData(
        holdings={
            asset["id"]: Holding(asset_id=asset["id"], balance=10.0, available=10.0, value=10.0)
            for asset in products
        },
        cash=0.0,
    )
    data.assets = {asset["id"]: asset for asset in products}
    return data


def _attribute_scenarios() -> list[tuple[str, dict]]:
    """(translation_key, published attributes) for every sensor class that
    publishes attributes. A translation_key may appear more than once, when
    different sensor states publish different, mutually exclusive attributes
    (PriceSensor's `conversion` vs. `conversion_rate`/`rate_date`/
    `rate_source`, depending on whether an ECB rate has loaded yet) -- the
    test unions every scenario sharing a key before comparing it to that
    key's labels, so this still proves each one has a label."""
    wallet_coordinator = _Coordinator(_wallet_portfolio_data())
    rewards = _Coordinator({_VSN["id"]: RewardTotals(
        gross=12.0, fee=2.4, net=9.6, count=3, last_at="2026-09-22T17:16:35Z")})
    earn = _Coordinator(EarnData(apr={_VSN["id"]: 0.0544}, offered=frozenset({_VSN["id"]})))

    price_with_rate = PriceSensor(
        _Coordinator({_BTC["id"]: 100.0}),
        _Coordinator(EcbRates(date="2026-09-24", rates={"USD": 1.1367})),
        "eid", _BTC, "USD",
    )
    price_with_rate._price_24h_ago = 90.0

    # No rate loaded yet: the mutually exclusive `conversion` status branch.
    price_without_rate = PriceSensor(
        _Coordinator({_BTC["id"]: 100.0}), _Coordinator(None), "eid", _BTC, "USD",
    )

    return [
        ("wallet", WalletSensor(
            wallet_coordinator, "eid", "EUR", _VSN, lambda _asset_id: False
        ).extra_state_attributes),
        ("staking", StakingSensor(
            wallet_coordinator, earn, rewards, "eid", "EUR", _VSN
        ).extra_state_attributes),
        ("wallet_total", WalletTotalSensor(
            wallet_coordinator, "eid", "EUR", _VSN
        ).extra_state_attributes),
        ("price", price_with_rate.extra_state_attributes),
        ("price", price_without_rate.extra_state_attributes),
        ("cash_plus", PortfolioCashPlusSensor(
            _Coordinator(_cash_plus_portfolio_data()), "eid", "EUR"
        ).extra_state_attributes),
    ]


def test_every_published_attribute_has_a_translated_label():
    strings = json.loads((_DIR / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((_DIR / "translations/en.json").read_text(encoding="utf-8"))

    published: dict[str, set[str]] = {}
    for translation_key, attrs in _attribute_scenarios():
        published.setdefault(translation_key, set()).update(attrs)

    for translation_key, attrs in published.items():
        labels = strings["entity"]["sensor"][translation_key]["state_attributes"]
        assert attrs == set(labels), translation_key
        assert english["entity"]["sensor"][translation_key]["state_attributes"] == labels, (
            translation_key
        )


def test_the_conversion_status_has_a_translated_name_and_state():
    """`conversion` is a status key, not a raw sentence: its own name plus a
    `state` translation for `no_rate` -- the only value it ever takes."""
    strings = json.loads((_DIR / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((_DIR / "translations/en.json").read_text(encoding="utf-8"))
    german = json.loads((_DIR / "translations/de.json").read_text(encoding="utf-8"))

    expected_en = {
        "name": "Conversion: status",
        "state": {"no_rate": "No exchange rate loaded yet"},
    }
    assert strings["entity"]["sensor"]["price"]["state_attributes"]["conversion"] == expected_en
    assert english["entity"]["sensor"]["price"]["state_attributes"]["conversion"] == expected_en
    assert german["entity"]["sensor"]["price"]["state_attributes"]["conversion"] == {
        "name": "Umrechnung: Status",
        "state": {"no_rate": "Noch kein Umrechnungskurs geladen"},
    }
