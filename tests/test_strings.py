"""The string files: structurally identical, BOM-free, and every translation
true to its English original in what it must carry over unchanged."""
import json
from pathlib import Path
import re
import string

from custom_components.bitpanda import migration
from custom_components.bitpanda.api import BitpandaApiError
from custom_components.bitpanda.assets import ASSET_CATEGORY_FILTERS, CATEGORY_OTHER
from custom_components.bitpanda.const import API_ERROR_KINDS, REQUIRED_SCOPES
from custom_components.bitpanda.ecb import EcbError, EcbRates
from custom_components.bitpanda.portfolio_coordinator import _update_failed
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
from custom_components.bitpanda.price_coordinator import ISSUE_SLOW_PRICE_INTERVAL, _ecb_failed
from custom_components.bitpanda.price_sensor import PriceSensor

_DIR = Path(__file__).parent.parent / "custom_components" / "bitpanda"
# Every language file under translations/, found the way the integration
# itself finds them (language.async_shipped_languages): a new one is guarded by
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
    assert _LANGUAGES == ["de", "en", "es", "fr", "it", "nl", "pl"]


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


# hassfest's pattern for a URL in a text (script/hassfest/translations.py,
# RE_URL, in 2026.9): it refuses a strings file that has one. A link target
# comes in as a placeholder the code fills in, as {api_key_url} does.
_URL = re.compile(
    r"(((ftp|ftps|scp|http|https|mqtt|mqtts|socket|socks5):\/\/|www\.)"
    r"[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?)",
    re.IGNORECASE,
)


def test_no_string_contains_a_url():
    for name in _FILES:
        for key, text in _texts(_load(name)).items():
            assert not _URL.search(text), (name, key)


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


# Home Assistant's own labels, per language, from its frontend translations as
# bundled with 2026.9: an integration entry's menu items "Reconfigure",
# "Configure" and "Delete" (ui.panel.config.integrations.config_entry
# .reconfigure / .configure / .delete) and a dialog's button
# (ui.panel.config.integrations.config_flow.submit, which is
# ui.common.submit). The button reads "Next" instead (config_flow.next: en
# "Next", de "Weiter", fr "Suivant", nl "Volgende", it "Prossimo", es
# "Siguiente", pl "Dalej") only on a step shown with last_step=False, and no
# step of this integration is.
_MENU_LABELS = {
    "de": {
        "reconfigure": "Neu konfigurieren", "configure": "Konfigurieren", "submit": "OK",
        "delete": "Löschen",
    },
    "en": {
        "reconfigure": "Reconfigure", "configure": "Configure", "submit": "Submit",
        "delete": "Delete",
    },
    "es": {
        "reconfigure": "Reconfigurar", "configure": "Configurar", "submit": "Enviar",
        "delete": "Eliminar",
    },
    "fr": {
        "reconfigure": "Reconfigurer", "configure": "Configurer", "submit": "Valider",
        "delete": "Supprimer",
    },
    "it": {
        "reconfigure": "Riconfigura", "configure": "Configura", "submit": "Invia",
        "delete": "Elimina",
    },
    "nl": {
        "reconfigure": "Herconfigureer", "configure": "Configureren", "submit": "Verzenden",
        "delete": "Verwijderen",
    },
    "pl": {
        "reconfigure": "Rekonfiguracja", "configure": "Konfiguruj", "submit": "Zatwierdź",
        "delete": "Usuń",
    },
}

# The texts that send the user to one of those controls, by the control.
_LABEL_REFERENCES = {
    "reconfigure": [
        ("config", "step", "portfolio", "description"),
        ("config", "step", "currency", "sections", "currency", "data_description", "currency"),
        ("options", "step", "portfolio", "description"),
        ("issues", "currency_dropped", "description"),
    ],
    "configure": [
        ("config", "step", "price_tracker", "description"),
        ("config", "step", "currency", "sections", "language", "data_description", "language"),
        ("config", "abort", "no_reconfigure"),
    ],
    "submit": [
        ("config", "step", "confirm_currency", "description"),
        ("config_subentries", "price_group", "step", "asset", "data_description", "asset"),
        ("config_subentries", "price_group", "step", "security", "data_description", "asset"),
    ],
    "delete": [
        ("issues", "portfolio_exists", "description"),
        ("exceptions", "portfolio_device_not_removable", "message"),
    ],
}


def _quoted(label: str) -> re.Pattern:
    """`label` in quotation marks: "…", „…“ or „…”, or « … » with no-break
    spaces."""
    return re.compile(rf"[\"„«]\s?{re.escape(label)}\s?[\"“”»]")


def test_menu_items_are_named_with_home_assistants_own_labels():
    """Where a text sends the user to a menu item of the integration entry or
    to a dialog's button, it names it in quotation marks exactly as the
    frontend labels it in that language."""
    assert sorted(_MENU_LABELS) == _LANGUAGES
    for language, labels in _MENU_LABELS.items():
        strings = _load(f"translations/{language}.json")
        for control, keys in _LABEL_REFERENCES.items():
            for key in keys:
                text = strings
                for part in key:
                    text = text[part]
                assert _quoted(labels[control]).search(text), (language, ".".join(key))


def _text(strings: dict, key: tuple[str, ...]) -> str:
    for part in key:
        strings = strings[part]
    return strings


# Where those controls sit, in Home Assistant's frontend at the 2025.5 floor as
# at 2026.9: "Reconfigure" and "Delete" in the ⋮ menu of an entry on the
# integration page; "Configure" on the entry itself (a labelled button before
# 2025.7, ⚙ from 2025.7); "Add price tracker" in the entry's ⋮ menu (from 2025.7
# also a button at the top of the integration page). A text that sends the user
# to one of them -- or to delete a device or a group, which the ⋮ menu on its
# page offers -- says where: on the Bitpanda integration page, by the entry's
# name, with the ⋮ or ⚙ to look for.
_INTEGRATION_PAGE = {
    "de": "Bitpanda-Integrationsseite",
    "en": "Bitpanda integration page",
    "es": "página de la integración Bitpanda",
    "fr": "page de l'intégration Bitpanda",
    "it": "pagina dell'integrazione Bitpanda",
    "nl": "integratiepagina van Bitpanda",
    "pl": "stronie integracji Bitpanda",
}
# Each text, and the symbol it points to ("" for "Add price tracker", a button
# or a menu item depending on the version).
_LOCATED_TEXTS = {
    ("config", "step", "portfolio", "description"): "⋮",
    ("config", "step", "currency", "sections", "currency", "data_description", "currency"): "⋮",
    ("options", "step", "portfolio", "description"): "⋮",
    ("issues", "currency_dropped", "description"): "⋮",
    ("config", "step", "price_tracker", "description"): "⚙",
    ("config", "step", "currency", "sections", "language", "data_description", "language"): "⚙",
    ("issues", "price_tracker_exists", "description"): "",
    ("issues", "portfolio_exists", "description"): "⋮",
    ("exceptions", "portfolio_device_not_removable", "message"): "⋮",
    ("issues", "slow_price_interval", "description"): "⋮",
}
# Shown right on the Price Tracker's entry, after its ⋮ -> "Reconfigure": it
# sends the user to "Configure" (⚙) on "the same entry".
_ON_THE_SAME_ENTRY = ("config", "abort", "no_reconfigure")


def test_texts_say_where_to_find_what_they_send_the_user_to():
    """For users new to Home Assistant: a text never names a menu item
    without saying where to find it."""
    assert sorted(_INTEGRATION_PAGE) == _LANGUAGES
    menu_items = {
        key for control in ("reconfigure", "configure", "delete")
        for key in _LABEL_REFERENCES[control]
    }
    assert menu_items - {_ON_THE_SAME_ENTRY} <= set(_LOCATED_TEXTS)
    for language in _LANGUAGES:
        strings = _load(f"translations/{language}.json")
        for key, symbol in _LOCATED_TEXTS.items():
            text = _text(strings, key)
            assert _INTEGRATION_PAGE[language] in text, (language, ".".join(key))
            assert symbol in text, (language, ".".join(key))
        assert "⚙" in _text(strings, _ON_THE_SAME_ENTRY), language


def test_texts_name_the_add_price_tracker_button_by_its_own_label():
    """The Price Tracker's "Add price tracker" is this integration's own text
    (`config_subentries.price_group.initiate_flow.user`): a text that sends
    the user to it quotes it exactly as the same file labels it."""
    for name in _FILES:
        strings = _load(name)
        label = strings["config_subentries"]["price_group"]["initiate_flow"]["user"]
        for key in (
            ("config", "step", "price_tracker", "description"),
            ("issues", "price_tracker_exists", "description"),
        ):
            text = strings
            for part in key:
                text = text[part]
            assert _quoted(label).search(text), (name, ".".join(key))


# Each shipped language by its own name.
_ENDONYMS = {
    "de": "Deutsch",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "it": "Italiano",
    "nl": "Nederlands",
    "pl": "Polski",
}


def test_every_shipped_language_is_offered_by_its_own_name():
    """The language setting (Configure, `selector.language`) lists every
    shipped language by its own name, the same in every file: whoever needs
    their language finds it, whatever language the list is shown in."""
    assert sorted(_ENDONYMS) == _LANGUAGES
    for name in _FILES:
        assert _load(name)["selector"]["language"]["options"] == _ENDONYMS, name


def test_each_service_has_options_texts_of_its_own():
    """Configure shows one form per service, each under its own step id
    (config_flow.BitpandaOptionsFlow), every field in a named section: the
    Price Tracker's in two, the Portfolio's language in one of its own,
    under the same heading as the Price Tracker's. Every field has a
    label and a help text, in its section. The Portfolio keeps its step
    text (where to find Reconfigure); the Price Tracker has none."""
    steps = _load("strings.json")["options"]["step"]
    assert set(steps) == {"price_tracker", "portfolio"}
    price_tracker, portfolio = steps["price_tracker"], steps["portfolio"]
    for step in (price_tracker, portfolio):
        assert "data" not in step and "data_description" not in step
    assert "description" not in price_tracker and portfolio["description"]
    assert list(price_tracker["sections"]) == ["currencies", "language"]
    assert list(portfolio["sections"]) == ["language"]
    assert set(price_tracker["sections"]["currencies"]["data"]) == {"extra_currencies"}
    assert set(price_tracker["sections"]["language"]["data"]) == {"language"}
    for texts in (*price_tracker["sections"].values(), *portfolio["sections"].values()):
        assert texts["name"]
        assert set(texts["data_description"]) == set(texts["data"])
    for name in _FILES:
        steps = _load(name)["options"]["step"]
        assert (
            steps["portfolio"]["sections"]["language"]["name"]
            == steps["price_tracker"]["sections"]["language"]["name"]
        ), name


# The label of the Price Tracker's currencies field under Configure: the
# currencies beside EUR, which every asset always has. A label cannot be left
# empty -- the frontend would show the key, and hassfest refuses blanks.
_IN_ADDITION_TO_EUR = {
    "de": "Zusätzlich zu EUR",
    "en": "In addition to EUR",
    "es": "Además de EUR",
    "fr": "En plus de l'EUR",
    "it": "Oltre a EUR",
    "nl": "Naast EUR",
    "pl": "Oprócz EUR",
}


def test_the_configure_currencies_field_says_what_comes_beside_eur():
    """So its help text no longer says that EUR always stays -- none does,
    in any language; it keeps what choosing a currency does and how its
    prices are converted, what removing one does, and that a removed
    currency's sensors keep their history."""
    assert sorted(_IN_ADDITION_TO_EUR) == _LANGUAGES
    for language, label in _IN_ADDITION_TO_EUR.items():
        currencies = _load(f"translations/{language}.json")["options"]["step"]["price_tracker"][
            "sections"
        ]["currencies"]
        assert currencies["data"]["extra_currencies"] == label, language
        assert "EUR" not in currencies["data_description"]["extra_currencies"], language
    help_texts = {
        language: _load(f"translations/{language}.json")["options"]["step"]["price_tracker"][
            "sections"
        ]["currencies"]["data_description"]["extra_currencies"]
        for language in ("en", "de")
    }
    assert help_texts == {
        "en": "Each selected currency adds one more sensor per asset, converted with the daily "
        "reference rates of the European Central Bank.\nRemoving a currency removes those "
        "sensors; their history is kept and comes back when you select the currency again.",
        "de": "Jede gewählte Währung fügt pro Asset einen weiteren Sensor hinzu, umgerechnet mit "
        "den täglichen Referenzkursen der Europäischen Zentralbank.\nWird eine Währung "
        "abgewählt, werden diese Sensoren entfernt; ihr Verlauf bleibt erhalten und ist wieder "
        "da, wenn du die Währung erneut wählst.",
    }


def test_the_setup_words_the_currencies_as_configure_does():
    """The Price Tracker's setup shows its currencies as Configure does: in a
    section of the same name, the field under the same label, and the same
    first sentence under it -- what a currency adds and how it is
    converted. Configure goes on, on a line of its own (the help text is
    Markdown with line breaks, at the 2025.5 floor as at 2026.9), to say
    what removing one does; at setup there is nothing to remove."""
    for name in _FILES:
        strings = _load(name)
        step = strings["config"]["step"]["price_tracker"]
        assert "data" not in step and "data_description" not in step, name
        setup = step["sections"]["currencies"]
        configure = strings["options"]["step"]["price_tracker"]["sections"]["currencies"]
        assert (setup["name"], setup["data"]) == (configure["name"], configure["data"]), name
        first = setup["data_description"]["extra_currencies"]
        assert configure["data_description"]["extra_currencies"].startswith(first + "\n"), name


def test_both_portfolio_setup_steps_carry_the_service_name():
    """The key step and the currency step are one dialog to the user: both
    titled with the service's name, as the Price Tracker's setup is, while
    their sections name what each asks for."""
    for name in _FILES:
        steps = _load(name)["config"]["step"]
        assert (steps["portfolio"]["title"], steps["currency"]["title"]) == (
            "Bitpanda Portfolio", "Bitpanda Portfolio",
        ), name


def test_the_setup_names_the_language_as_configure_does():
    """Each service's setup -- the Price Tracker's, the Portfolio's currency
    step -- asks for the language in a section worded like its own Configure
    section: one setting, one wording, wherever it is set. The Portfolio's
    help text goes on to say where to change the language later; the Price
    Tracker's text above its form says so already, for both of its
    settings."""
    for name in _FILES:
        strings = _load(name)
        configure = strings["options"]["step"]
        steps = strings["config"]["step"]
        assert (
            steps["price_tracker"]["sections"]["language"]
            == configure["price_tracker"]["sections"]["language"]
        ), name
        portfolio = steps["currency"]["sections"]["language"]
        own = configure["portfolio"]["sections"]["language"]
        assert (portfolio["name"], portfolio["data"]) == (own["name"], own["data"]), name
        assert portfolio["data_description"]["language"].startswith(
            own["data_description"]["language"] + " "
        ), name


def test_the_price_tracker_names_its_language_by_its_own_field():
    """Where a Price Tracker text sends the user to its language setting --
    the answer to its "Reconfigure" -- it names it as the Price Tracker's own
    field does, group titles alone: never as the Portfolio's, which also
    covers messages the Price Tracker does not write."""
    for name in _FILES:
        strings = _load(name)
        steps = strings["options"]["step"]
        tracker = steps["price_tracker"]["sections"]["language"]["data"]["language"].casefold()
        portfolio = steps["portfolio"]["sections"]["language"]["data"]["language"].casefold()
        text = strings["config"]["abort"]["no_reconfigure"].casefold()
        assert tracker in text and portfolio not in text, name


def test_the_language_field_says_what_it_sets_for_each_service():
    """Each service's language field names what follows it: the Price
    Tracker's its group titles alone -- it writes no messages of its own --
    the Portfolio's also the message why a device cannot be deleted. The
    help text gives the crypto group's own title as its example and names
    what follows the other two languages."""
    for name in _FILES:
        strings = _load(name)
        crypto = strings["selector"]["asset_group"]["options"]["crypto"]
        steps = strings["options"]["step"]
        tracker = steps["price_tracker"]["sections"]["language"]
        portfolio = steps["portfolio"]["sections"]["language"]
        assert tracker["data"]["language"] != portfolio["data"]["language"], name
        for texts in (tracker, portfolio):
            assert crypto in texts["data_description"]["language"], name
    shown = {
        language: {
            service: (
                texts["data"]["language"],
                texts["data_description"]["language"],
            )
            for service in ("price_tracker", "portfolio")
            for texts in [
                _load(f"translations/{language}.json")["options"]["step"][service]["sections"][
                    "language"
                ]
            ]
        }
        for language in ("en", "de")
    }
    assert shown == {
        "en": {
            "price_tracker": (
                "Language of group titles",
                'Group titles, such as "Cryptocurrencies", appear in this language. Sensor names '
                "follow Home Assistant's system language, dialogs and attribute names the "
                "language of your user profile.",
            ),
            "portfolio": (
                "Language of group titles and messages",
                'Group titles, such as "Cryptocurrencies", appear in this language, and so does '
                "the message explaining why a device cannot be deleted. Sensor names follow Home "
                "Assistant's system language, dialogs and attribute names the language of your "
                "user profile.",
            ),
        },
        "de": {
            "price_tracker": (
                "Sprache der Gruppentitel",
                "Gruppentitel wie „Kryptowährungen“ erscheinen in dieser Sprache. Sensornamen "
                "folgen der Systemsprache von Home Assistant, Dialoge und Attributnamen der "
                "Sprache deines Benutzerprofils.",
            ),
            "portfolio": (
                "Sprache für Gruppentitel und Meldungen",
                "Gruppentitel wie „Kryptowährungen“ erscheinen in dieser Sprache, ebenso die "
                "Meldung, warum sich ein Gerät nicht löschen lässt. Sensornamen folgen der "
                "Systemsprache von Home Assistant, Dialoge und Attributnamen der Sprache deines "
                "Benutzerprofils.",
            ),
        },
    }


def test_the_setup_menu_says_what_each_service_is_for():
    """The setup menu names each service with nothing but whether it needs an
    API key. The text above it says what each one is for, as a list of its
    own after a blank line with each service's name in bold -- which Home
    Assistant 2025.5 renders as 2026.9 does, unlike descriptions under each
    menu item. In the approved English and German wording."""
    for name in _FILES:
        step = _load(name)["config"]["step"]["user"]
        question, services = step["description"].split("\n\n")
        assert "\n" not in question, name
        portfolio, tracker = services.split("\n")
        assert portfolio.startswith("- **Bitpanda Portfolio**"), name
        assert tracker.startswith("- **Bitpanda Price Tracker**"), name
        assert step["menu_options"]["portfolio"].startswith("Bitpanda Portfolio ("), name
        assert step["menu_options"]["price_tracker"].startswith("Bitpanda Price Tracker ("), name
        assert all(label.endswith(")") for label in step["menu_options"].values()), name
    # French and Dutch say prices as their other Price Tracker texts do.
    menu = {name: _load(name)["config"]["step"]["user"]["description"] for name in _FILES}
    assert "les prix en direct" in menu["translations/fr.json"]
    assert "actuele prijzen" in menu["translations/nl.json"]
    assert _load("strings.json")["config"]["step"]["user"] == {
        "title": "Bitpanda",
        "description": (
            "Which service do you want to set up? Each one can be added once.\n\n"
            "- **Bitpanda Portfolio**: your account \u2013 everything you hold at Bitpanda.\n"
            "- **Bitpanda Price Tracker**: live prices of the assets you choose \u2013 whether"
            " you hold them or not."
        ),
        "menu_options": {
            "portfolio": "Bitpanda Portfolio (API key required)",
            "price_tracker": "Bitpanda Price Tracker (no API key required)",
        },
    }
    assert _load("translations/de.json")["config"]["step"]["user"] == {
        "title": "Bitpanda",
        "description": (
            "Welchen Dienst möchtest du einrichten? Jeder lässt sich einmal hinzufügen.\n\n"
            "- **Bitpanda Portfolio**: dein Konto \u2013 alles, was du bei Bitpanda hältst.\n"
            "- **Bitpanda Price Tracker**: Live-Preise der Assets, die du auswählst \u2013 auch"
            " ohne sie zu besitzen."
        ),
        "menu_options": {
            "portfolio": "Bitpanda Portfolio (API-Schlüssel benötigt)",
            "price_tracker": "Bitpanda Price Tracker (kein API-Schlüssel benötigt)",
        },
    }


def test_the_portfolio_setup_walks_through_creating_the_key():
    """The Portfolio's setup step says what the service shows, then walks
    through creating the key as a numbered list of its own between blank
    lines -- open the key page, choose the permissions with the trading
    permission set off by a dash, paste the key -- and ends with a line each on what the key
    allows, how long it is valid and where to replace it. Its field has no
    help text: the step text is the guide, and a key that lacks a
    permission gets the error that says so. In the approved English and
    German wording."""
    for name in _FILES:
        step = _load(name)["config"]["step"]["portfolio"]
        assert set(step) == {"title", "description", "data"}, name
        shows, needs, guide, key = step["description"].split("\n\n")
        assert "\n" not in shows + needs, name
        open_page, permissions, paste = guide.split("\n")
        assert open_page.startswith("1. ") and "[{api_key_url}]({api_key_url})" in open_page, name
        chosen, left_out = permissions.split(" \u2013 ")
        assert chosen.startswith("2. "), name
        *required, trade = _PERMISSION_LABELS[_language(name)]
        assert all(label in chosen for label in required) and trade in left_out, name
        assert trade not in chosen, name
        assert paste.startswith("3. "), name
        assert len(key.split("\n")) == 3, name
    assert _load("strings.json")["config"]["step"]["portfolio"] == {
        "title": "Bitpanda Portfolio",
        "description": (
            "The Bitpanda Portfolio shows your Bitpanda account in Home Assistant: its total"
            " value, your returns, and a wallet for every asset you hold. The integration"
            " creates the wallets itself and removes them when you no longer hold an asset"
            " \u2013 you do not need to add or delete any.\n\n"
            "For this, the integration needs an API key. To create one:\n\n"
            "1. Open [{api_key_url}]({api_key_url}) and create a new key.\n"
            '2. Select only the permissions "Balances", "Transaction" and "Earn (Read)"'
            ' \u2013 not "Trade (Read)".\n'
            "3. Copy the key and paste it below. Bitpanda shows it only once.\n\n"
            "The integration only reads with it: it cannot trade or move money.\n"
            "Bitpanda keys are valid until the date you choose when creating them, one year at"
            " most; after that, Home Assistant asks for a new one.\n"
            'You can replace the key at any time: open the ⋮ menu of the "Bitpanda Portfolio"'
            ' entry on the Bitpanda integration page and choose "Reconfigure".'
        ),
        "data": {"api_key": "API key"},
    }
    assert _load("translations/de.json")["config"]["step"]["portfolio"] == {
        "title": "Bitpanda Portfolio",
        "description": (
            "Das Bitpanda Portfolio zeigt dein Bitpanda-Konto in Home Assistant: den"
            " Gesamtwert, deine Renditen und für jedes Asset, das du besitzt, ein eigenes"
            " Wallet. Die Wallets legt die Integration selbst an und entfernt sie wieder, wenn"
            " du ein Asset nicht mehr besitzt \u2013 hinzufügen oder löschen musst du nichts.\n\n"
            "Dafür braucht die Integration einen API-Schlüssel. So erstellst du ihn:\n\n"
            "1. Öffne [{api_key_url}]({api_key_url}) und erstelle einen neuen Schlüssel.\n"
            "2. Wähle nur die Berechtigungen „Guthaben“, „Transaktion“ und „Earn (Read)“"
            " \u2013 kein „Trading (Read)“.\n"
            "3. Kopiere den Schlüssel und füge ihn unten ein. Bitpanda zeigt ihn nur einmal"
            " an.\n\n"
            "Die Integration liest damit nur: Handeln oder Geld bewegen kann sie nicht.\n"
            "Bitpanda-Schlüssel gelten bis zu dem Datum, das du beim Erstellen wählst,"
            " höchstens ein Jahr; danach fragt Home Assistant nach einem neuen.\n"
            "Ersetzen kannst du den Schlüssel jederzeit: Öffne auf der"
            " Bitpanda-Integrationsseite das Menü ⋮ beim Eintrag „Bitpanda Portfolio“ und"
            " wähle „Neu konfigurieren“."
        ),
        "data": {"api_key": "API-Schlüssel"},
    }


def test_the_reconfigure_key_help_has_a_line_per_sentence():
    """Under Reconfigure's key field: that an empty field keeps the key, and
    on a line of its own what a new key needs -- with the trading permission
    set off by a dash, as in the setup's guide. In the approved English and German
    wording."""
    help_texts = {
        name: _load(name)["config"]["step"]["reconfigure"]["data_description"]["api_key"]
        for name in _FILES
    }
    for name, help_text in help_texts.items():
        keep, new_key = help_text.split("\n")
        assert "[{api_key_url}]({api_key_url})" in new_key, name
        chosen, left_out = new_key.split(" \u2013 ")
        *required, trade = _PERMISSION_LABELS[_language(name)]
        assert all(label in chosen for label in required) and trade in left_out, name
        assert trade not in keep + chosen, name
    assert help_texts["strings.json"] == (
        "Leave empty to keep the current key.\n"
        'A new key from [{api_key_url}]({api_key_url}) needs the permissions "Balances",'
        ' "Transaction" and "Earn (Read)" \u2013 not "Trade (Read)".'
    )
    assert help_texts["translations/de.json"] == (
        "Lass das Feld leer, um den aktuellen Schlüssel zu behalten.\n"
        "Ein neuer Schlüssel von [{api_key_url}]({api_key_url}) braucht die Berechtigungen"
        " „Guthaben“, „Transaktion“ und „Earn (Read)“ \u2013 kein „Trading (Read)“."
    )


def test_the_reauth_dialog_starts_what_to_do_on_a_line_of_its_own():
    """The new-key dialog says what happened and why, then -- on a line of
    its own -- where to create the new key and that the sensors are kept.
    Under the field, what the new key needs, with the trading permission set
    off by a dash as in the setup's guide. In the approved English and German wording."""
    steps = {name: _load(name)["config"]["step"]["reauth_confirm"] for name in _FILES}
    texts = {
        name: (step["description"], step["data_description"]["api_key"])
        for name, step in steps.items()
    }
    for name, (description, help_text) in texts.items():
        happened, to_do = description.split("\n")
        assert "{api_key_url}" not in happened and "[{api_key_url}]({api_key_url})" in to_do, name
        chosen, left_out = help_text.split(" \u2013 ")
        *required, trade = _PERMISSION_LABELS[_language(name)]
        assert all(label in chosen for label in required) and trade in left_out, name
        assert trade not in chosen, name
    assert texts["strings.json"] == (
        "Bitpanda rejected the stored API key. It may have expired, or it predates the"
        " permissions this version needs.\n"
        "Create a new key at [{api_key_url}]({api_key_url}) and paste it here. Your sensors"
        " are kept.",
        'The new key needs the permissions "Balances", "Transaction" and "Earn (Read)"'
        ' \u2013 not "Trade (Read)".',
    )
    assert texts["translations/de.json"] == (
        "Bitpanda hat den gespeicherten API-Schlüssel abgelehnt. Er ist vielleicht abgelaufen,"
        " oder er stammt aus der Zeit vor den Berechtigungen, die diese Version braucht.\n"
        "Erstelle unter [{api_key_url}]({api_key_url}) einen neuen Schlüssel und füge ihn hier"
        " ein. Deine Sensoren bleiben erhalten.",
        "Der neue Schlüssel braucht die Berechtigungen „Guthaben“, „Transaktion“ und"
        " „Earn (Read)“ \u2013 kein „Trading (Read)“.",
    )


def test_the_old_statistics_step_explains_both_choices():
    """The setup's question about old statistics: what happened, in one
    paragraph with both currencies; then a list item per button, led by the
    button's own label in bold, each saying it sets up the Portfolio in the
    new currency; the second links Troubleshooting through a placeholder, as
    hassfest allows no URL in a text. Last, in a paragraph of its own, the
    way back: closing the dialog keeps the old statistics. In the approved
    English and German wording."""
    for name in _FILES:
        step = _load(name)["config"]["step"]["old_statistics"]
        assert set(step) == {"title", "description", "menu_options"}, name
        assert set(step["menu_options"]) == {"delete_statistics", "keep_statistics"}, name
        intro, choices, way_back = step["description"].split("\n\n")
        assert "\n" not in intro and _placeholders(intro) == {"old", "new"}, name
        delete, keep = choices.split("\n")
        for item, option, placeholders in (
            (delete, "delete_statistics", {"new"}),
            (keep, "keep_statistics", {"new", "troubleshooting_url"}),
        ):
            label = re.escape(step["menu_options"][option])
            assert re.match(rf"- \*\*{label}\s?:\*\* ", item), (name, option)
            assert _placeholders(item) == placeholders, (name, option)
        assert _LINK_TARGET.findall(intro + delete + way_back) == [], name
        assert "\n" not in way_back and _placeholders(way_back) == set(), name
        assert "X" in way_back, name
        assert _LINK_TARGET.findall(keep) == ["{troubleshooting_url}"], name
    assert _load("strings.json")["config"]["step"]["old_statistics"] == {
        "title": "Old statistics in another currency",
        "description": (
            "Home Assistant still holds long-term statistics of an earlier Bitpanda Portfolio"
            " in {old}. You chose {new}. A sensor whose statistics are in another currency"
            " records no new statistics until the old ones are gone.\n\n"
            "- **Delete and set up:** deletes the history and long-term statistics of every"
            " earlier Portfolio sensor – figures, returns and wallets – and sets up the"
            " Portfolio in {new}. Its statistics then start afresh. The deleted data cannot be"
            " restored.\n"
            "- **Keep and set up:** sets up the Portfolio in {new} and deletes nothing. The"
            " sensors with old statistics record none until you delete the old statistics"
            " yourself; [Troubleshooting]({troubleshooting_url}) in the README explains how.\n\n"
            'To keep the old statistics, close this dialog with the "X" instead: nothing is set'
            " up or deleted then. Set up the Portfolio again in their currency, and they continue."
        ),
        "menu_options": {
            "delete_statistics": "Delete and set up",
            "keep_statistics": "Keep and set up",
        },
    }
    assert _load("translations/de.json")["config"]["step"]["old_statistics"] == {
        "title": "Alte Statistiken in anderer Währung",
        "description": (
            "Home Assistant hat noch Langzeitstatistiken eines früheren Bitpanda Portfolios in"
            " {old}. Du hast {new} gewählt. Ein Sensor, dessen Statistik in einer anderen"
            " Währung vorliegt, zeichnet keine neue Statistik auf, bis die alte weg ist.\n\n"
            "- **Löschen und einrichten:** löscht Verlauf und Langzeitstatistiken aller"
            " früheren Portfolio-Sensoren – Kennzahlen, Renditen und Wallets – und richtet"
            " das Portfolio in {new} ein. Seine Statistik beginnt dann neu. Die gelöschten"
            " Daten lassen sich nicht wiederherstellen.\n"
            "- **Behalten und einrichten:** richtet das Portfolio in {new} ein und löscht"
            " nichts. Die Sensoren mit alter Statistik zeichnen keine auf, bis du die alte"
            " Statistik selbst löschst; [Troubleshooting]({troubleshooting_url}) in der README"
            " erklärt, wie.\n\n"
            "Möchtest du die alte Statistik behalten, schließe den Dialog stattdessen über das"
            " „X“: Dann wird nichts eingerichtet oder gelöscht. Richte das Portfolio danach in"
            " ihrer Währung ein, dann läuft sie weiter."
        ),
        "menu_options": {
            "delete_statistics": "Löschen und einrichten",
            "keep_statistics": "Behalten und einrichten",
        },
    }


# Bitpanda's permission names as its key page shows them in each language
# (read by the maintainer on 2026-09-29), in that language's quotation marks:
# Balances, Transaction, Earn (Read), Trade (Read). A language Bitpanda's
# website does not offer takes the English names.
_PERMISSION_LABELS = {
    "de": ("„Guthaben“", "„Transaktion“", "„Earn (Read)“", "„Trading (Read)“"),
    "en": ('"Balances"', '"Transaction"', '"Earn (Read)"', '"Trade (Read)"'),
    "es": ('"Créditos"', '"Transacción"', '"Earn (Lectura)"', '"Trading (Lectura)"'),
    "fr": (
        "« Soldes »",
        "« Transactions »",
        "« Earn (Lecture) »",
        "« Trader (Lecture) »",
    ),
    "it": ('"Saldi"', '"Transazione"', '"Earn (Lettura)"', '"Trading (Lettura)"'),
    "nl": ('"Saldi"', '"Transactie"', '"Earn (Lezen)"', '"Traden (Lezen)"'),
    "pl": ("„Salda”", "„Transakcja”", "„Earn (Odczytaj)”", "„Trade (Odczytaj)”"),
}


def _language(name: str) -> str:
    """The language of a string file: strings.json is English."""
    return "en" if name == "strings.json" else Path(name).stem


def test_the_missing_permissions_error_marks_each_permission():
    """The error names the key's three permissions as Bitpanda's key page
    does in each language, each followed by the mark the code fills in --
    ✓ or ✗, never a word -- and asks for a new key with all three. In the
    approved English and German wording."""
    assert sorted(_PERMISSION_LABELS) == _LANGUAGES
    for name in _FILES:
        error = _load(name)["config"]["error"]["missing_scopes"]
        *required, trade = _PERMISSION_LABELS[_language(name)]
        assert _placeholders(error) == set(REQUIRED_SCOPES), name
        for label, scope in zip(required, REQUIRED_SCOPES):
            assert f"{label} {{{scope}}}" in error, name
        assert trade not in error, name
    assert _load("strings.json")["config"]["error"]["missing_scopes"] == (
        'Permissions of this API key: "Balances" {balance}, "Transaction" {transaction},'
        ' "Earn (Read)" {earn}. Permissions cannot be added to an existing key. Create a new'
        " one with all three."
    )
    assert _load("translations/de.json")["config"]["error"]["missing_scopes"] == (
        "Berechtigungen dieses API-Schlüssels: „Guthaben“ {balance}, „Transaktion“"
        " {transaction}, „Earn (Read)“ {earn}. Einem bestehenden Schlüssel lassen sich"
        " keine Berechtigungen hinzufügen. Erstelle einen neuen mit allen dreien."
    )


# A German text names the key's permissions when it says Berechtigung or
# names one of them -- but Guthaben alone, which is also the German name of
# the balance sensors.
_PERMISSION_MARKERS = ("Berechtigung", "Transaktion", "Earn (Read)", "Trading")


def test_german_texts_quote_the_permission_names():
    """Wherever a German text names the key's permissions, it quotes them,
    as Bitpanda's key page labels them: „Guthaben“, „Transaktion“,
    „Earn (Read)“ and „Trading (Read)“ -- in the setup's guide, the reauth and
    the reconfigure help as in the missing-permissions error."""
    unquoted = [
        (key, name)
        for key, text in _texts(_load("translations/de.json")).items()
        if any(marker in text for marker in _PERMISSION_MARKERS)
        for name in ("Guthaben", "Transaktion", "Earn (Read)", "Trading (Read)")
        if name in text.replace(f"„{name}“", "")
    ]
    assert unquoted == []


def test_no_language_but_german_names_a_permission_in_german():
    """Outside German every text names the key's permissions in its own
    language (_PERMISSION_LABELS): none carries Guthaben or Transaktion."""
    for name in _FILES:
        if _language(name) != "de":
            german = [
                key for key, text in _texts(_load(name)).items()
                if "Guthaben" in text or "Transaktion" in text
            ]
            assert german == [], name


def test_the_refresh_action_says_what_it_does():
    """The action picker shows this text alone. It says what the action
    fetches, that the call waits for it, that a call within the cooldown is
    ignored and that a failed refresh fails the call -- in the approved
    English and German wording."""
    assert _load("strings.json")["services"]["refresh"]["description"] == (
        "Fetches the portfolio and the prices from Bitpanda now and waits until both are "
        "done. Ignored within the cooldown of the last call; fails when a refresh fails."
    )
    assert _load("translations/de.json")["services"]["refresh"]["description"] == (
        "Holt Portfolio und Preise sofort und wartet, bis beides fertig ist. Innerhalb der "
        "Sperrzeit ignoriert; schlägt fehl, wenn eine Aktualisierung fehlschlägt."
    )


# The one step whose field has no help text: the Portfolio's setup, whose step
# text above its key field is the guide to creating the key.
_WITHOUT_HELP_TEXT = {"config.portfolio"}


def test_every_field_has_a_help_text():
    """Under every field of every dialog -- setup, reauth, reconfigure,
    Configure and "Add price tracker" -- a help text (`data_description`)
    says what it is for: exactly one per labelled field, except where the
    step text is the guide to its field. The flow tests check that every
    field a form shows is labelled."""
    strings = _load("strings.json")
    steps = {
        **{f"config.{step_id}": step for step_id, step in strings["config"]["step"].items()},
        **{f"options.{step_id}": step for step_id, step in strings["options"]["step"].items()},
        **{
            f"config_subentries.{flow}.{step_id}": step
            for flow, texts in strings["config_subentries"].items()
            for step_id, step in texts["step"].items()
        },
    }
    labelled = {name: step for name, step in steps.items() if step.get("data")}
    labelled |= {
        f"{name}.sections.{key}": texts
        for name, step in steps.items()
        for key, texts in step.get("sections", {}).items()
    }
    assert len(labelled) == 13
    for name, step in labelled.items():
        helped = set() if name in _WITHOUT_HELP_TEXT else set(step["data"])
        assert set(step.get("data_description", {})) == helped, name


# --- Failed requests: one text per kind of failure ---------------------------------


def _failure_texts() -> dict[str, list[tuple[str, dict[str, str] | None]]]:
    """The (translation key, placeholders) of every text a failed request can
    raise, by the coordinator module that raises it: one per kind of failure
    (const.API_ERROR_KINDS) and the plain one for a failure that says too
    little -- each with the placeholders the code fills in."""
    bitpanda = [
        BitpandaApiError("English detail", kind=kind, path="/portfolio", status=503)
        for kind in API_ERROR_KINDS
    ] + [BitpandaApiError("English detail")]
    ecb = [EcbError("English detail", kind=kind, status=503) for kind in API_ERROR_KINDS] + [
        EcbError("English detail")
    ]
    return {
        "portfolio_coordinator": [
            (failed.translation_key, failed.translation_placeholders)
            for failed in map(_update_failed, bitpanda)
        ],
        "price_coordinator": [
            (failed.translation_key, failed.translation_placeholders)
            for failed in map(_ecb_failed, ecb)
        ],
    }


def test_each_kind_of_failed_request_has_a_text_of_its_own():
    """Every kind has a text of its own for Bitpanda's requests. The ECB
    fetch answers no listing and has no rate limit of its own -- a 429 from
    it is an HTTP status -- so those two kinds, like a failure without a
    kind, get its plain text."""
    texts = _failure_texts()
    kinds = [*API_ERROR_KINDS, None]
    bitpanda = dict(zip(kinds, (key for key, _ in texts["portfolio_coordinator"])))
    assert len(set(bitpanda.values())) == len(kinds)
    assert bitpanda[None] == "update_failed"
    assert bitpanda["rate_limited"] == "update_failed_rate_limited"
    ecb = dict(zip(kinds, (key for key, _ in texts["price_coordinator"])))
    plain = {"incomplete_listing", "rate_limited", None}
    assert {ecb[kind] for kind in plain} == {"ecb_rates_failed"}
    own = [ecb[kind] for kind in kinds if kind not in plain]
    assert len(set(own)) == len(own) == 4
    assert "ecb_rates_failed" not in own


def test_every_failure_text_has_exactly_the_placeholders_the_code_fills_in():
    """A missing placeholder would show as `{path}`, an extra one would be
    dropped; and none of them carries words -- the request path, an HTTP
    status -- so the whole message is in the reader's language."""
    for name in _FILES:
        exceptions = _load(name)["exceptions"]
        for texts in _failure_texts().values():
            for key, placeholders in texts:
                assert _placeholders(exceptions[key]["message"]) == set(placeholders or {}), (
                    name, key
                )


def test_no_exception_text_takes_an_english_message():
    """`{error}` once carried the API client's English message into
    otherwise translated texts."""
    for name in _FILES:
        for key, text in _texts(_load(name)["exceptions"]).items():
            assert "error" not in _placeholders(text), (name, key)


def test_every_issue_text_is_one_the_code_raises():
    """strings.json holds no repair-issue text the code never raises: the
    upgrade's reports, what blocks the upgrade, and the Price Tracker's slow
    interval. Each module's own tests render its issues in every language."""
    assert set(_load("strings.json")["issues"]) == {
        *migration.UPGRADE_ISSUES,
        *migration.BLOCKER_ISSUES,
        ISSUE_SLOW_PRICE_INTERVAL,
    }


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


# The three sensors of a wallet device, by translation key, named by the part
# of the balance each shows, in sentence case: "Balance (available)", never
# "Balance (Available)".
_WALLET_PART_NAMES = {
    "de": ("Guthaben (verfügbar)", "Guthaben (Staking)", "Guthaben (gesamt)"),
    "en": ("Balance (available)", "Balance (staking)", "Balance (total)"),
    "es": ("Saldo (disponible)", "Saldo (staking)", "Saldo (total)"),
    "fr": ("Solde (disponible)", "Solde (staking)", "Solde (total)"),
    "it": ("Saldo (disponibile)", "Saldo (staking)", "Saldo (totale)"),
    "nl": ("Saldo (beschikbaar)", "Saldo (staking)", "Saldo (totaal)"),
    "pl": ("Saldo (dostępne)", "Saldo (staking)", "Saldo (łącznie)"),
}


def test_the_wallet_sensors_are_named_by_their_part_of_the_balance():
    """The Wallet sensor has a name of its own, not its device's: "Vision
    (VSN) Wallet Balance (available)" beside "… Balance (staking)" and
    "… Balance (total)"."""
    assert sorted(_WALLET_PART_NAMES) == _LANGUAGES
    for language, names in _WALLET_PART_NAMES.items():
        sensors = _load(f"translations/{language}.json")["entity"]["sensor"]
        assert tuple(
            sensors[key]["name"] for key in ("wallet", "staking", "wallet_total")
        ) == names, language


def test_the_price_group_flow_has_its_strings():
    strings = json.loads((_DIR / "strings.json").read_text(encoding="utf-8"))
    assert set(strings["config_subentries"]) == {"price_group", "wallet_group"}
    group = strings["config_subentries"]["price_group"]
    assert set(group["step"]) == {"user", "asset", "security"}
    assert set(group["abort"]) == {"already_configured", "asset_added"}
    assert "{asset}" in group["abort"]["asset_added"]
    assert "{group}" in group["abort"]["asset_added"]


def test_only_the_securities_search_names_the_isin():
    """Stocks, ETFs and ETCs show their ISIN in the list, the other asset
    types have none: only the securities' step says it can be searched for.
    Otherwise both steps are the same dialog -- title, text and label."""
    for name in _FILES:
        steps = _load(name)["config_subentries"]["price_group"]["step"]
        asset, security = steps["asset"], steps["security"]
        assert "ISIN" in security["data_description"]["asset"], name
        assert "ISIN" not in asset["data_description"]["asset"], name
        assert [asset[key] for key in ("title", "description", "data")] == [
            security[key] for key in ("title", "description", "data")
        ], name


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

    def __init__(self, data=None, last_update_success=True, data_available=None):
        self.data = data
        self.last_update_success = last_update_success
        self.data_available = last_update_success if data_available is None else data_available


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
# An ETF: every sensor of a stock, ETF or ETC adds its ISIN.
_ETF = {"id": "1f0ed6c9-ee10-68c6-8a0e-55a29b7757fe", "symbol": "LYY1",
        "name": "Amundi PEA S&P 500 UCITS ETF", "isin": "FR0011871136",
        "type": "equity_security", "group": "equity_etf"}


def _wallet_portfolio_data() -> PortfolioData:
    """A holding of VSN and of the ETF, each with every performance figure
    set, so WalletTotalSensor publishes the full performance set -- and
    WalletSensor, which never carries it, has no label for it."""
    data = PortfolioData(
        holdings={
            asset["id"]: Holding(
                asset_id=asset["id"], balance=100.0, available=25.0, value=200.0,
                invested=150.0, avg_buy_price=1.5, total_return=50.0, total_return_pct=33.33,
            )
            for asset in (_VSN, _ETF)
        },
        cash=0.0,
    )
    data.assets = {asset["id"]: asset for asset in (_VSN, _ETF)}
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
    etf_price = PriceSensor(_Coordinator({_ETF["id"]: 100.0}), None, "eid", _ETF, "EUR")

    wallet_parts = [
        scenario
        for asset in (_VSN, _ETF)
        for scenario in (
            ("wallet", WalletSensor(
                wallet_coordinator, "eid", "EUR", asset
            ).extra_state_attributes),
            ("staking", StakingSensor(
                wallet_coordinator, earn, rewards, "eid", "EUR", asset
            ).extra_state_attributes),
            ("wallet_total", WalletTotalSensor(
                wallet_coordinator, "eid", "EUR", asset
            ).extra_state_attributes),
        )
    ]
    return [
        *wallet_parts,
        ("price", price_with_rate.extra_state_attributes),
        ("price", price_without_rate.extra_state_attributes),
        ("price", etf_price.extra_state_attributes),
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


# The label of `asset_isin`, with the prefix of the other asset attributes of
# its language -- French with a no-break space before the colon.
_ISIN_LABELS = {
    "de": "Asset: ISIN",
    "en": "Asset: ISIN",
    "es": "Activo: ISIN",
    "fr": "Actif\u00a0: ISIN",
    "it": "Asset: ISIN",
    "nl": "Asset: ISIN",
    "pl": "Aktywo: ISIN",
}


def test_the_isin_is_labelled_on_every_sensor_that_names_its_asset():
    assert sorted(_ISIN_LABELS) == _LANGUAGES
    for language, label in _ISIN_LABELS.items():
        sensors = _load(f"translations/{language}.json")["entity"]["sensor"]
        for key in ("price", "wallet", "staking", "wallet_total"):
            assert sensors[key]["state_attributes"]["asset_isin"] == {"name": label}, (
                language, key,
            )


# The lifetime reward attributes of the Staking sensor, by language. German
# and Polish avoid their word for payouts ("Auszahlungen", "wypłaty"), which
# also reads as money taken out, and speak of credits instead.
_REWARD_LABELS = {
    "de": {
        "rewards_count": "Belohnungen: Anzahl Gutschriften",
        "rewards_gross": "Belohnungen: brutto (Menge)",
        "rewards_fee": "Belohnungen: Gebühr (Menge)",
        "rewards_net": "Belohnungen: netto (Menge)",
        "rewards_net_value": "Belohnungen: Wert netto (aktuell)",
        "rewards_last_at": "Belohnungen: zuletzt",
    },
    "en": {
        "rewards_count": "Rewards: number of payouts",
        "rewards_gross": "Rewards: gross (quantity)",
        "rewards_fee": "Rewards: fee (quantity)",
        "rewards_net": "Rewards: net (quantity)",
        "rewards_net_value": "Rewards: net value (current)",
        "rewards_last_at": "Rewards: last",
    },
    "es": {
        "rewards_count": "Recompensas: número de pagos",
        "rewards_gross": "Recompensas: bruto (cantidad)",
        "rewards_fee": "Recompensas: comisión (cantidad)",
        "rewards_net": "Recompensas: neto (cantidad)",
        "rewards_net_value": "Recompensas: valor neto (actual)",
        "rewards_last_at": "Recompensas: último pago",
    },
    "fr": {
        "rewards_count": "Récompenses\u00a0: nombre de versements",
        "rewards_gross": "Récompenses\u00a0: brut (quantité)",
        "rewards_fee": "Récompenses\u00a0: frais (quantité)",
        "rewards_net": "Récompenses\u00a0: net (quantité)",
        "rewards_net_value": "Récompenses\u00a0: valeur nette (actuelle)",
        "rewards_last_at": "Récompenses\u00a0: dernier versement",
    },
    "it": {
        "rewards_count": "Ricompense: numero di accrediti",
        "rewards_gross": "Ricompense: lordo (quantità)",
        "rewards_fee": "Ricompense: commissione (quantità)",
        "rewards_net": "Ricompense: netto (quantità)",
        "rewards_net_value": "Ricompense: valore netto (attuale)",
        "rewards_last_at": "Ricompense: ultimo accredito",
    },
    "nl": {
        "rewards_count": "Beloningen: aantal uitbetalingen",
        "rewards_gross": "Beloningen: bruto (hoeveelheid)",
        "rewards_fee": "Beloningen: kosten (hoeveelheid)",
        "rewards_net": "Beloningen: netto (hoeveelheid)",
        "rewards_net_value": "Beloningen: nettowaarde (actueel)",
        "rewards_last_at": "Beloningen: laatste uitbetaling",
    },
    "pl": {
        "rewards_count": "Nagrody: liczba naliczeń",
        "rewards_gross": "Nagrody: brutto (ilość)",
        "rewards_fee": "Nagrody: opłata (ilość)",
        "rewards_net": "Nagrody: netto (ilość)",
        "rewards_net_value": "Nagrody: wartość netto (bieżąca)",
        "rewards_last_at": "Nagrody: ostatnie naliczenie",
    },
}


def test_the_reward_attributes_say_what_they_count():
    """ "Rewards: count" passed for a sum of money. The count is the number
    of payouts; gross, fee and net are quantities of the asset, named with
    the word the language uses for `units` ("Asset: Menge"); the net value is
    today's. Only the labels change: the keys, which templates use, stay."""
    assert sorted(_REWARD_LABELS) == _LANGUAGES
    for language, labels in _REWARD_LABELS.items():
        attributes = _load(f"translations/{language}.json")["entity"]["sensor"]["staking"][
            "state_attributes"
        ]
        assert {key: attributes[key]["name"] for key in labels} == labels, language
        quantity = attributes["units"]["name"].split(":", 1)[1].strip()
        for key in ("rewards_gross", "rewards_fee", "rewards_net"):
            assert labels[key].endswith(f" ({quantity})"), (language, key)


# The position performance on a wallet's Total sensor, by language, in the
# order of _POSITION_KEYS. French puts a no-break space before the colon and
# the percent sign.
_POSITION_KEYS = ("average_buy_price", "invested_amount", "total_return", "total_return_percent")
_POSITION_LABELS = {
    "de": (
        "Bilanz: Ø Kaufpreis", "Bilanz: investiert", "Bilanz: Gewinn/Verlust",
        "Bilanz: Gewinn/Verlust %",
    ),
    "en": (
        "Position: average buy price", "Position: invested", "Position: profit/loss",
        "Position: profit/loss %",
    ),
    "es": (
        "Posición: precio medio de compra", "Posición: importe invertido",
        "Posición: ganancia/pérdida", "Posición: ganancia/pérdida %",
    ),
    "fr": (
        "Position\u00a0: prix d'achat moyen", "Position\u00a0: montant investi",
        "Position\u00a0: gain/perte", "Position\u00a0: gain/perte en\u00a0%",
    ),
    "it": (
        "Posizione: prezzo medio di acquisto", "Posizione: importo investito",
        "Posizione: profitto/perdita", "Posizione: profitto/perdita %",
    ),
    "nl": (
        "Positie: gemiddelde aankoopprijs", "Positie: geïnvesteerd bedrag",
        "Positie: winst/verlies", "Positie: winst/verlies %",
    ),
    "pl": (
        "Pozycja: średnia cena zakupu", "Pozycja: zainwestowana kwota",
        "Pozycja: zysk/strata", "Pozycja: zysk/strata %",
    ),
}


def test_the_position_figures_are_not_labelled_like_the_wallet_sensors():
    """The Total sensor lists the position's performance under a prefix of
    its own, the same for all four: never the word the wallet sensors are
    named with, or "Balance (total)" would list "Balance: invested" -- one
    word for two things. Only the labels say so: the keys, which templates
    use, stay."""
    assert sorted(_POSITION_LABELS) == _LANGUAGES
    for language, labels in _POSITION_LABELS.items():
        sensors = _load(f"translations/{language}.json")["entity"]["sensor"]
        attributes = sensors["wallet_total"]["state_attributes"]
        assert tuple(attributes[key]["name"] for key in _POSITION_KEYS) == labels, language
        prefixes = {label.split(":", 1)[0].strip() for label in labels}
        assert len(prefixes) == 1, (language, prefixes)
        [prefix] = prefixes
        for key in ("wallet", "staking", "wallet_total"):
            assert not sensors[key]["name"].startswith(prefix), (language, key)


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
