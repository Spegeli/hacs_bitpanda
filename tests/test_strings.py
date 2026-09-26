"""The string files: structurally identical, BOM-free, and every translation
true to its English original in what it must carry over unchanged."""
import json
from pathlib import Path
import re
import string

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
# Every language file under translations/, found the way the integration
# itself finds them (groups._shipped_languages): a new one is guarded by
# every test below as soon as it exists.
_LANGUAGES = sorted(path.stem for path in (_DIR / "translations").glob("*.json"))
_FILES = ("strings.json", *(f"translations/{language}.json" for language in _LANGUAGES))


def _load(name: str) -> dict:
    return json.loads((_DIR / name).read_text(encoding="utf-8"))


def _paths(node, prefix: str = "") -> set[str]:
    if not isinstance(node, dict):
        return set()
    out: set[str] = set()
    for key, value in node.items():
        out.add(prefix + key)
        out |= _paths(value, f"{prefix}{key}.")
    return out


def _texts(node, prefix: str = "") -> dict[str, str]:
    """Every string of a strings file, by its dotted key."""
    if isinstance(node, str):
        return {prefix[:-1]: node}
    out: dict[str, str] = {}
    for key, value in node.items():
        out |= _texts(value, f"{prefix}{key}.")
    return out


def test_the_shipped_languages():
    assert _LANGUAGES == ["de", "en"]


def test_string_files_have_no_bom():
    for name in _FILES:
        assert not (_DIR / name).read_bytes().startswith(b"\xef\xbb\xbf"), name


def test_string_files_share_one_structure():
    reference = _paths(_load("strings.json"))
    for name in _FILES:
        structure = _paths(_load(name))
        assert structure == reference, (
            name, sorted(reference - structure), sorted(structure - reference)
        )


def _placeholders(text: str) -> set[str]:
    """The {placeholders} of a string, parsed as Home Assistant parses them
    when it checks a translation against English (string.Formatter)."""
    return {field for _, field, _, _ in string.Formatter().parse(text) if field is not None}


def test_every_string_has_the_placeholders_of_its_english_original():
    """Home Assistant discards a translated string whose placeholders differ
    from the English one and shows English instead; and a value only appears
    where its placeholder is."""
    english = _texts(_load("strings.json"))
    for name in _FILES:
        for key, text in _texts(_load(name)).items():
            assert _placeholders(text) == _placeholders(english[key]), (name, key)


def test_no_apostrophe_directly_precedes_a_placeholder():
    """The frontend formats strings as ICU messages, where an apostrophe right
    before a brace opens literal text: "l'{asset}" would show "{asset}"
    itself and swallow the text up to the next apostrophe. Easily written in
    French or Italian -- write around it."""
    for name in _FILES:
        for key, text in _texts(_load(name)).items():
            assert "'{" not in text, (name, key)


_LINK_TARGET = re.compile(r"\]\(([^)]*)\)")


def test_every_link_keeps_its_english_target():
    english = _texts(_load("strings.json"))
    for name in _FILES:
        for key, text in _texts(_load(name)).items():
            assert _LINK_TARGET.findall(text) == _LINK_TARGET.findall(english[key]), (
                name, key
            )


def test_no_language_is_an_untranslated_copy_of_english():
    """Codes, product names and a few loanwords ("EUR", "Cash Plus",
    "Staking") may read the same in every language. A sentence never does,
    and most strings must differ."""
    english = _texts(_load("strings.json"))
    for language in _LANGUAGES:
        if language == "en":
            continue
        texts = _texts(_load(f"translations/{language}.json"))
        same = sorted(key for key, text in texts.items() if text == english[key])
        sentences = [key for key in same if len(english[key].split()) >= 4]
        assert sentences == [], (language, sentences)
        assert len(same) * 5 <= len(texts), (language, same)


def test_every_language_titles_each_group_differently():
    """Groups are told apart by their titles; a title is also how a group is
    recognised as a shipped default when it is retitled (groups.py)."""
    for name in _FILES:
        titles = list(_load(name)["selector"]["asset_group"]["options"].values())
        assert len(set(titles)) == len(titles), name


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
