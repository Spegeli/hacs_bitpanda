"""The string files: structurally identical, BOM-free, and every translation
true to its English original in what it must carry over unchanged."""
from datetime import timedelta
import json
from pathlib import Path
import re
import string

from homeassistant.util import dt as dt_util

from custom_components.bitpanda import migration
from custom_components.bitpanda.api import BitpandaApiError
from custom_components.bitpanda.assets import (
    ASSET_CATEGORIES,
    ASSET_CATEGORY_FILTERS,
    CATEGORY_OTHER,
)
from custom_components.bitpanda.const import (
    API_ERROR_KINDS,
    PRICE_TRACKER_ISSUES,
    REQUIRED_SCOPES,
)
from custom_components.bitpanda.announcements import PORTFOLIO_EVENT_TYPES
from custom_components.bitpanda.ecb import EcbError, EcbRates
from custom_components.bitpanda.portfolio_coordinator import _update_failed
from custom_components.bitpanda.portfolio_model import (
    EarnData,
    EarnProduct,
    Holding,
    PortfolioData,
    PortfolioReturns,
    RewardPayout,
    RewardTotals,
)
from custom_components.bitpanda.portfolio_sensor import (
    PortfolioCashPlusSensor,
    PortfolioClassSensor,
    PortfolioInvestedSensor,
    PortfolioReturnSensor,
    PortfolioTotalReturnPercentSensor,
    PortfolioTotalReturnSensor,
    StakingSensor,
    WalletSensor,
    WalletTotalSensor,
)
from custom_components.bitpanda.price_coordinator import _ecb_failed
from custom_components.bitpanda.price_sensor import PriceSensor

from tests.conftest import ANNOUNCEMENT_FIELDS, assert_issue_texts_render

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
# step of this integration is. And, as bundled with 2026.10, the way to a
# dashboard card: "Edit dashboard" (ui.panel.lovelace.menu.configure_ui),
# "Add card" (ui.panel.lovelace.editor.section.add_card, the same as
# .editor.edit_card.add), the card dialog's "By card" tab
# (ui.panel.lovelace.editor.cardpicker.by_card: the dialog opens on "By entity"),
# "Add dashboard"
# (ui.panel.config.lovelace.dashboards.picker.add_dashboard), "Settings"
# (panel.config), "Dashboards" (ui.panel.config.dashboard.dashboards.main)
# and the Overview's sidebar label (panel.home). And, read from the frontends
# of 2025.5.0 and 2026.10.1 alike ("es", not "es-419"): "Add service" at the
# top of the integration page of a service integration
# (ui.panel.config.integrations.integration_page.add_service), and the way to
# a new integration, "Devices & services" (ui.panel.config.dashboard.devices
# .main) and "Add integration" (ui.panel.config.integrations.add_integration).
_MENU_LABELS = {
    "de": {
        "devices_services": "Geräte & Dienste", "add_integration": "Integration hinzufügen", "add_service": "Dienst hinzufügen", "reconfigure": "Neu konfigurieren", "configure": "Konfigurieren", "submit": "OK",
        "delete": "Löschen", "edit_dashboard": "Dashboard bearbeiten",
        "add_card": "Karte hinzufügen", "by_card": "Nach Karte", "add_dashboard": "Dashboard hinzufügen",
        "settings": "Einstellungen", "dashboards": "Dashboards", "overview": "Übersicht",
    },
    "en": {
        "devices_services": "Devices & services", "add_integration": "Add integration", "add_service": "Add service", "reconfigure": "Reconfigure", "configure": "Configure", "submit": "Submit",
        "delete": "Delete", "edit_dashboard": "Edit dashboard", "add_card": "Add card", "by_card": "By card",
        "add_dashboard": "Add dashboard", "settings": "Settings", "dashboards": "Dashboards",
        "overview": "Overview",
    },
    "es": {
        "devices_services": "Dispositivos y servicios", "add_integration": "Añadir integración", "add_service": "Añadir servicio", "reconfigure": "Reconfigurar", "configure": "Configurar", "submit": "Enviar",
        "delete": "Eliminar", "edit_dashboard": "Editar panel de control",
        "add_card": "Añadir tarjeta", "by_card": "Por tarjeta", "add_dashboard": "Añadir panel de control",
        "settings": "Configuración", "dashboards": "Paneles de control",
        "overview": "Vista general",
    },
    "fr": {
        "devices_services": "Appareils et services", "add_integration": "Ajouter une intégration", "add_service": "Ajouter un service", "reconfigure": "Reconfigurer", "configure": "Configurer", "submit": "Valider",
        "delete": "Supprimer", "edit_dashboard": "Modifier le tableau de bord",
        "add_card": "Ajouter une carte", "by_card": "Par carte", "add_dashboard": "Ajouter un tableau de bord",
        "settings": "Paramètres", "dashboards": "Tableaux de bord", "overview": "Vue d’ensemble",
    },
    "it": {
        "devices_services": "Dispositivi e servizi", "add_integration": "Aggiungi integrazione", "add_service": "Aggiungi servizio", "reconfigure": "Riconfigura", "configure": "Configura", "submit": "Invia",
        "delete": "Elimina", "edit_dashboard": "Modifica la plancia", "add_card": "Aggiungi scheda", "by_card": "Per scheda",
        "add_dashboard": "Aggiungi plancia", "settings": "Impostazioni", "dashboards": "Plance",
        "overview": "Panoramica",
    },
    "nl": {
        "devices_services": "Apparaten en diensten", "add_integration": "Integratie toevoegen", "add_service": "Dienst toevoegen", "reconfigure": "Herconfigureer", "configure": "Configureren", "submit": "Verzenden",
        "delete": "Verwijderen", "edit_dashboard": "Dashboard bewerken",
        "add_card": "Kaart toevoegen", "by_card": "Per kaart", "add_dashboard": "Dashboard toevoegen",
        "settings": "Instellingen", "dashboards": "Dashboards", "overview": "Thuis",
    },
    "pl": {
        "devices_services": "Urządzenia oraz usługi", "add_integration": "Dodaj integrację", "add_service": "Dodaj usługę", "reconfigure": "Rekonfiguracja", "configure": "Konfiguruj", "submit": "Zatwierdź",
        "delete": "Usuń", "edit_dashboard": "Edytuj panel", "add_card": "Dodaj kartę", "by_card": "Według karty",
        "add_dashboard": "Dodaj panel", "settings": "Ustawienia", "dashboards": "Panele",
        "overview": "Przegląd",
    },
}

# The texts that send the user to one of those controls, by the control.
_LABEL_REFERENCES = {
    "add_service": [
        ("issues", "portfolio_required", "description"),
        ("config_subentries", "price_group", "abort", "portfolio_required"),
    ],
    "devices_services": [("config", "abort", "portfolio_required")],
    "add_integration": [("config", "abort", "portfolio_required")],
    "reconfigure": [
        ("config", "step", "portfolio", "description"),
        ("config", "step", "currency", "sections", "currency", "data_description", "currency"),
        ("options", "step", "portfolio", "description"),
        ("issues", "currency_dropped", "description"),
    ],
    "configure": [
        ("config", "step", "price_tracker", "description"),
        ("config", "step", "currency", "sections", "language", "data_description", "language"),
        ("config", "step", "currency", "sections", "notifications", "description"),
        ("config", "abort", "no_reconfigure"),
    ],
    "submit": [
        ("config_subentries", "price_group", "step", "asset", "data_description", "asset"),
        ("config_subentries", "price_group", "step", "security", "data_description", "asset"),
    ],
    "delete": [
        ("issues", "portfolio_exists", "description"),
        ("exceptions", "portfolio_device_not_removable", "message"),
        ("config", "step", "reauth_confirm", "description"),
        ("config", "step", "reconfigure", "description"),
    ],
    **{
        control: [("config", "create_entry", "portfolio"), ("config", "create_entry", "price_tracker")]
        for control in (
            "edit_dashboard", "add_card", "by_card", "add_dashboard", "settings", "dashboards", "overview"
        )
    },
}
# The menu's abort sends the user to "Add integration" by way of "Settings".
_LABEL_REFERENCES["settings"] = [*_LABEL_REFERENCES["settings"], ("config", "abort", "portfolio_required")]


def _quoted(label: str) -> re.Pattern:
    """`label` in quotation marks: "…", „…“ or „…”, or « … » with no-break
    spaces."""
    return re.compile(rf"[\"„«]\s?{re.escape(label)}\s?[\"“”»]")


def test_menu_items_are_named_with_home_assistants_own_labels():
    """Where a text sends the user to a menu item of the integration entry,
    to a dialog's button or along the way to a dashboard card, it names it
    in quotation marks exactly as the frontend labels it in that language."""
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
    ("config", "step", "currency", "sections", "notifications", "description"): "⚙",
    ("issues", "price_tracker_exists", "description"): "",
    ("issues", "portfolio_exists", "description"): "⋮",
    ("exceptions", "portfolio_device_not_removable", "message"): "⋮",
    ("config", "step", "reauth_confirm", "description"): "⋮",
    ("config", "step", "reconfigure", "description"): "⋮",
    ("config", "create_entry", "price_tracker"): "",
    ("issues", "portfolio_required", "description"): "",
}
# Shown right on the Price Tracker's entry, after its ⋮ -> "Reconfigure": it
# sends the user to "Configure" (⚙) on "the same entry".
_ON_THE_SAME_ENTRY = ("config", "abort", "no_reconfigure")


def test_the_deletion_dialog_names_its_button_as_home_assistant_names_delete():
    """The dialog of the entities not migrated deletes: its button says so,
    with Home Assistant's own label for Delete, and its text quotes it."""
    for language, labels in _MENU_LABELS.items():
        confirm = _load(f"translations/{language}.json")["issues"]["entities_not_migrated"][
            "fix_flow"
        ]["step"]["confirm"]
        assert confirm["submit"] == labels["delete"], language
        assert _quoted(labels["delete"]).search(confirm["description"]), language


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
            ("config", "create_entry", "price_tracker"),
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
    Price Tracker's in two, the Portfolio's notifications in one of their
    own, then its language under the same heading as the Price Tracker's --
    the language last in every form. Every field has a label and a help
    text, in its section. The Portfolio keeps its step
    text (where to find Reconfigure); the Price Tracker has none."""
    steps = _load("strings.json")["options"]["step"]
    assert set(steps) == {"price_tracker", "portfolio"}
    price_tracker, portfolio = steps["price_tracker"], steps["portfolio"]
    for step in (price_tracker, portfolio):
        assert "data" not in step and "data_description" not in step
    assert "description" not in price_tracker and portfolio["description"]
    assert list(price_tracker["sections"]) == ["currencies", "language"]
    assert list(portfolio["sections"]) == ["notifications", "language"]
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
    the Portfolio's also the message why a device cannot be deleted and the
    notifications chosen in its "Notifications" section, worded generically
    so that a later notification needs no new text. The help text gives the
    crypto group's own title as its example and names what follows the other
    two languages."""
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
                'Group titles, such as "Cryptocurrencies", appear in this language, and so do '
                "the message explaining why a device cannot be deleted and the notifications you "
                'choose in the "Notifications" section. Sensor names follow Home Assistant\'s '
                "system language, dialogs and attribute names the language of your user profile.",
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
                "Meldung, warum sich ein Gerät nicht löschen lässt, und die Benachrichtigungen, "
                "die du im Abschnitt „Benachrichtigungen“ auswählst. Sensornamen folgen der "
                "Systemsprache von Home Assistant, Dialoge und Attributnamen der Sprache deines "
                "Benutzerprofils.",
            ),
        },
    }


# The Portfolio's notifications, as approved on 2026-10-03: the section's
# name -- Home Assistant's own name for its notification drawer in each
# language -- the switch's label, its help text, alike in setup and in
# Configure, and the setup section's description: where to change the
# notification settings later, once for every switch the section may hold.
_NOTIFICATIONS_SECTION = {
    "en": (
        "Notifications",
        "Notify about new wallets",
        'When a new wallet appears in the Portfolio, after you buy an asset for example, Home '
        'Assistant shows a notification under "Notifications". Wallets present when the '
        "Portfolio was set up do not count. Automations can react to the event "
        "`bitpanda_wallet_added` either way.",
        'You can change the notification settings later with "Configure" (⚙) on the "Bitpanda '
        'Portfolio" entry of the Bitpanda integration page.',
    ),
    "de": (
        "Benachrichtigungen",
        "Bei neuen Wallets benachrichtigen",
        "Kommt im Portfolio ein neues Wallet dazu, etwa nach dem Kauf eines Assets, zeigt Home "
        "Assistant eine Benachrichtigung unter „Benachrichtigungen“. Wallets, die es bei der "
        "Einrichtung schon gab, zählen nicht. Automationen können in jedem Fall auf das "
        "Ereignis `bitpanda_wallet_added` reagieren.",
        "Die Benachrichtigungseinstellungen kannst du später mit „Konfigurieren“ (⚙) beim "
        "Eintrag „Bitpanda Portfolio“ auf der Bitpanda-Integrationsseite ändern.",
    ),
    "fr": (
        "Notifications",
        "Signaler les nouveaux wallets",
        "Lorsqu'un nouveau wallet apparaît dans le Portfolio, par exemple après l'achat d'un "
        "actif, Home Assistant affiche une notification dans «\u00a0Notifications\u00a0». Les "
        "wallets présents lors de la configuration du Portfolio ne comptent pas. Les "
        "automatisations peuvent réagir à l'événement `bitpanda_wallet_added` dans tous les "
        "cas.",
        "Vous pourrez modifier les paramètres de notification plus tard avec «\u00a0Configurer"
        "\u00a0» (⚙) sur l'entrée «\u00a0Bitpanda Portfolio\u00a0» de la page de l'intégration "
        "Bitpanda.",
    ),
    "nl": (
        "Meldingen",
        "Melding bij nieuwe wallets",
        "Komt er een nieuwe wallet bij in het Portfolio, bijvoorbeeld nadat je een asset hebt "
        'gekocht, dan toont Home Assistant een melding onder "Meldingen". Wallets die er al '
        "waren toen het Portfolio werd ingesteld, tellen niet mee. Automatiseringen kunnen in "
        "elk geval reageren op de gebeurtenis `bitpanda_wallet_added`.",
        'Je kunt de meldingsinstellingen later wijzigen via "Configureren" (⚙) bij de invoer '
        '"Bitpanda Portfolio" op de integratiepagina van Bitpanda.',
    ),
    "it": (
        "Notifiche",
        "Notifica per i nuovi wallet",
        "Quando nel Portfolio compare un nuovo wallet, per esempio dopo l'acquisto di un asset, "
        'Home Assistant mostra una notifica in "Notifiche". I wallet già presenti quando il '
        "Portfolio è stato configurato non contano. Le automazioni possono reagire in ogni caso "
        "all'evento `bitpanda_wallet_added`.",
        'Puoi modificare le impostazioni delle notifiche in seguito con "Configura" (⚙) sulla '
        'voce "Bitpanda Portfolio" nella pagina dell\'integrazione Bitpanda.',
    ),
    "es": (
        "Notificaciones",
        "Avisar de los wallets nuevos",
        "Cuando aparece un wallet nuevo en el Portfolio, por ejemplo después de comprar un "
        'activo, Home Assistant muestra una notificación en "Notificaciones". Los wallets que ya '
        "existían al configurar el Portfolio no cuentan. Las automatizaciones pueden reaccionar "
        "al evento `bitpanda_wallet_added` en cualquier caso.",
        'Puedes cambiar los ajustes de notificación más adelante con "Configurar" (⚙) en la '
        'entrada "Bitpanda Portfolio" de la página de la integración Bitpanda.',
    ),
    "pl": (
        "Powiadomienia",
        "Powiadamiaj o nowych portfelach",
        "Gdy w Portfolio pojawi się nowy portfel, na przykład po zakupie aktywa, Home Assistant "
        "wyświetli powiadomienie w panelu „Powiadomienia”. Portfele istniejące w chwili "
        "konfiguracji Portfolio się nie liczą. Automatyzacje mogą w każdym przypadku reagować na "
        "zdarzenie `bitpanda_wallet_added`.",
        "Ustawienia powiadomień możesz później zmienić, klikając „Konfiguruj” (⚙) przy wpisie "
        "„Bitpanda Portfolio” na stronie integracji Bitpanda.",
    ),
}


# The staking reward switch, after the wallet switch in the same section
# (issue #13).
_STAKING_SWITCH = {
    "en": (
        "Notify about staking rewards",
        'When Bitpanda pays out a staking reward, Home Assistant shows a notification under '
        '"Notifications": one per asset, which the next payout replaces. Payouts missed while '
        "Home Assistant was off are added up in one notification per asset. Only assets with an "
        "enabled Balance (staking) sensor count. Automations can react to the event "
        "`bitpanda_staking_reward_received` either way.",
    ),
    "de": (
        "Bei Staking-Belohnungen benachrichtigen",
        "Zahlt Bitpanda eine Staking-Belohnung aus, zeigt Home Assistant eine Benachrichtigung "
        "unter „Benachrichtigungen“: eine pro Asset, die nächste Auszahlung ersetzt sie. "
        "Auszahlungen, die Home Assistant verpasst hat, weil es aus war, fasst es pro Asset in "
        "einer Benachrichtigung zusammen. Es zählen nur Assets mit aktiviertem Sensor "
        "„Guthaben (Staking)“. Automationen können in jedem Fall auf das Ereignis "
        "`bitpanda_staking_reward_received` reagieren.",
    ),
    "fr": (
        "Signaler les récompenses de staking",
        "Lorsque Bitpanda verse une récompense de staking, Home Assistant affiche une "
        "notification dans «\u00a0Notifications\u00a0»\u00a0: une par actif, que le versement "
        "suivant remplace. Les versements manqués pendant que Home Assistant était éteint sont "
        "additionnés dans une seule notification par actif. Seuls les actifs dont le capteur "
        "«\u00a0Solde (staking)\u00a0» est activé comptent. Les automatisations peuvent réagir à "
        "l'événement `bitpanda_staking_reward_received` dans tous les cas.",
    ),
    "nl": (
        "Melding bij stakingbeloningen",
        'Keert Bitpanda een stakingbeloning uit, dan toont Home Assistant een melding onder '
        '"Meldingen": één per asset, en de volgende uitbetaling vervangt die. Uitbetalingen die '
        "Home Assistant heeft gemist omdat het uit stond, worden per asset in één melding "
        'opgeteld. Alleen assets met een ingeschakelde sensor "Saldo (staking)" tellen mee. '
        "Automatiseringen kunnen in elk geval reageren op de gebeurtenis "
        "`bitpanda_staking_reward_received`.",
    ),
    "it": (
        "Notifica per le ricompense di staking",
        "Quando Bitpanda accredita una ricompensa di staking, Home Assistant mostra una notifica "
        'in "Notifiche": una per asset, che l\'accredito successivo sostituisce. Gli accrediti '
        "persi mentre Home Assistant era spento vengono sommati in una sola notifica per asset. "
        'Contano solo gli asset con il sensore "Saldo (staking)" abilitato. Le automazioni '
        "possono reagire in ogni caso all'evento `bitpanda_staking_reward_received`.",
    ),
    "es": (
        "Avisar de las recompensas de staking",
        "Cuando Bitpanda paga una recompensa de staking, Home Assistant muestra una notificación "
        'en "Notificaciones": una por activo, que el siguiente pago sustituye. Los pagos que Home '
        "Assistant se perdió mientras estaba apagado se suman en una sola notificación por "
        'activo. Solo cuentan los activos con el sensor "Saldo (staking)" habilitado. Las '
        "automatizaciones pueden reaccionar al evento `bitpanda_staking_reward_received` en "
        "cualquier caso.",
    ),
    "pl": (
        "Powiadamiaj o nagrodach za staking",
        "Gdy Bitpanda wypłaci nagrodę za staking, Home Assistant wyświetli powiadomienie w panelu "
        "„Powiadomienia”: jedno na aktywo, a następna wypłata je zastępuje. Wypłaty pominięte, gdy "
        "Home Assistant był wyłączony, są sumowane w jednym powiadomieniu na aktywo. Liczą się "
        "tylko aktywa z włączonym sensorem „Saldo (staking)”. Automatyzacje mogą w każdym "
        "przypadku reagować na zdarzenie `bitpanda_staking_reward_received`.",
    ),
}


def test_the_notifications_section_says_what_it_switches():
    """Two switches in a section of its own -- new wallets, then staking
    rewards --, worded alike in setup and in Configure; the setup's section
    adds where to change the notification settings later, once for every
    switch it holds."""
    assert sorted(_NOTIFICATIONS_SECTION) == sorted(_STAKING_SWITCH) == _LANGUAGES
    for language, (name, label, help_text, later) in _NOTIFICATIONS_SECTION.items():
        staking_label, staking_help = _STAKING_SWITCH[language]
        strings = _load(f"translations/{language}.json")
        configure = strings["options"]["step"]["portfolio"]["sections"]["notifications"]
        setup = strings["config"]["step"]["currency"]["sections"]["notifications"]
        data = {"notify_new_wallets": label, "notify_staking_rewards": staking_label}
        descriptions = {
            "notify_new_wallets": help_text, "notify_staking_rewards": staking_help,
        }
        for section in (configure, setup):
            assert list(section["data"]) == list(section["data_description"]) == list(data)
        assert configure == {
            "name": name, "data": data, "data_description": descriptions,
        }, language
        assert setup == {
            "name": name, "description": later, "data": data, "data_description": descriptions,
        }, language


_CURRENCY_STEP_DESCRIPTIONS = {
    "en": "The API key works. Now choose your portfolio's currency, which notifications you want, "
    "and the language of group titles and messages.",
    "de": "Der API-Schlüssel funktioniert. Wähle jetzt die Währung deines Portfolios, welche "
    "Benachrichtigungen du möchtest, und die Sprache für Gruppentitel und Meldungen.",
    "fr": "La clé API fonctionne. Choisissez maintenant la devise de votre portefeuille, les "
    "notifications que vous souhaitez et la langue des titres de groupe et des messages.",
    "nl": "De API-sleutel werkt. Kies nu de valuta van je portfolio, welke meldingen je wilt "
    "ontvangen en de taal van groepstitels en meldingen.",
    "it": "La chiave API funziona. Ora scegli la valuta del tuo portafoglio, quali notifiche vuoi "
    "ricevere e la lingua dei titoli dei gruppi e dei messaggi.",
    "es": "La clave API funciona. Ahora elige la moneda de tu cartera, qué notificaciones quieres "
    "recibir y el idioma de los títulos de grupo y de los mensajes.",
    "pl": "Klucz API działa. Teraz wybierz walutę swojego portfolio, powiadomienia, które chcesz "
    "otrzymywać, oraz język tytułów grup i komunikatów.",
}


def test_the_currency_step_names_what_it_asks_for():
    """The currency, the notifications -- named generically, so that a
    later notification needs no new text -- and the language, in the order
    of the step's sections."""
    assert sorted(_CURRENCY_STEP_DESCRIPTIONS) == _LANGUAGES
    for language, description in _CURRENCY_STEP_DESCRIPTIONS.items():
        step = _load(f"translations/{language}.json")["config"]["step"]["currency"]
        assert step["description"] == description, language
        assert list(step["sections"]) == ["currency", "notifications", "language"], language


# The notification about a new wallet, in each entry language: its title and
# its message, whose link text is the wallet's name and whose target the
# wallet's device page.
_WALLET_ADDED = {
    "en": (
        "New Bitpanda wallet",
        "The Portfolio added a new wallet: **[{wallet}]({link})** in the group {group}.",
    ),
    "de": (
        "Neues Bitpanda-Wallet",
        "Das Portfolio hat ein neues Wallet angelegt: **[{wallet}]({link})** in der Gruppe "
        "{group}.",
    ),
    "fr": (
        "Nouveau wallet Bitpanda",
        "Le Portfolio a ajouté un nouveau wallet\u00a0: **[{wallet}]({link})** dans le groupe "
        "{group}.",
    ),
    "nl": (
        "Nieuwe Bitpanda-wallet",
        "Het Portfolio heeft een nieuwe wallet toegevoegd: **[{wallet}]({link})** in de groep "
        "{group}.",
    ),
    "it": (
        "Nuovo wallet Bitpanda",
        "Il Portfolio ha aggiunto un nuovo wallet: **[{wallet}]({link})** nel gruppo {group}.",
    ),
    "es": (
        "Nuevo wallet de Bitpanda",
        "El Portfolio ha añadido un wallet nuevo: **[{wallet}]({link})** en el grupo {group}.",
    ),
    "pl": (
        "Nowy portfel Bitpanda",
        "Portfolio dodało nowy portfel: **[{wallet}]({link})** w grupie {group}.",
    ),
}


def test_the_new_wallet_notification_texts():
    assert sorted(_WALLET_ADDED) == _LANGUAGES
    for language, (title, message) in _WALLET_ADDED.items():
        exceptions = _load(f"translations/{language}.json")["exceptions"]
        assert (
            exceptions["wallet_added_title"]["message"], exceptions["wallet_added"]["message"]
        ) == (title, message), language


# The notification about new staking payouts: one, or several added up; the
# value of the net amount only where a price is known (issue #13).
_STAKING_REWARD = {
    "en": (
        "New Bitpanda staking reward",
        "**[{wallet}]({link})** received a staking reward of **{net} {symbol}**.",
        "**[{wallet}]({link})** received {count} staking rewards, together **{net} {symbol}**.",
        "Worth about {value} {currency} today.",
    ),
    "de": (
        "Neue Bitpanda-Staking-Belohnung",
        "**[{wallet}]({link})** hat eine Staking-Belohnung von **{net} {symbol}** erhalten.",
        "**[{wallet}]({link})** hat {count} Staking-Belohnungen erhalten, zusammen "
        "**{net} {symbol}**.",
        "Heute etwa {value} {currency} wert.",
    ),
    "fr": (
        "Nouvelle récompense de staking Bitpanda",
        "**[{wallet}]({link})** a reçu une récompense de staking de **{net} {symbol}**.",
        "**[{wallet}]({link})** a reçu {count} récompenses de staking, au total "
        "**{net} {symbol}**.",
        "Valeur actuelle\u00a0: environ {value} {currency}.",
    ),
    "nl": (
        "Nieuwe Bitpanda-stakingbeloning",
        "**[{wallet}]({link})** heeft een stakingbeloning van **{net} {symbol}** ontvangen.",
        "**[{wallet}]({link})** heeft {count} stakingbeloningen ontvangen, samen "
        "**{net} {symbol}**.",
        "Vandaag ongeveer {value} {currency} waard.",
    ),
    "it": (
        "Nuova ricompensa di staking Bitpanda",
        "**[{wallet}]({link})** ha ricevuto una ricompensa di staking di **{net} {symbol}**.",
        "**[{wallet}]({link})** ha ricevuto {count} ricompense di staking, in totale "
        "**{net} {symbol}**.",
        "Valore attuale: circa {value} {currency}.",
    ),
    "es": (
        "Nueva recompensa de staking de Bitpanda",
        "**[{wallet}]({link})** ha recibido una recompensa de staking de **{net} {symbol}**.",
        "**[{wallet}]({link})** ha recibido {count} recompensas de staking, en total "
        "**{net} {symbol}**.",
        "Valor actual: unos {value} {currency}.",
    ),
    "pl": (
        "Nowa nagroda za staking Bitpanda",
        "**[{wallet}]({link})** otrzymał nagrodę za staking: **{net} {symbol}**.",
        "**[{wallet}]({link})** otrzymał nagrody za staking (liczba wypłat: {count}), łącznie "
        "**{net} {symbol}**.",
        "Obecna wartość: około {value} {currency}.",
    ),
}


def test_the_staking_reward_notification_texts():
    assert sorted(_STAKING_REWARD) == _LANGUAGES
    for language, texts in _STAKING_REWARD.items():
        exceptions = _load(f"translations/{language}.json")["exceptions"]
        assert tuple(
            exceptions[key]["message"]
            for key in (
                "staking_reward_title", "staking_reward", "staking_rewards",
                "staking_reward_value",
            )
        ) == texts, language


# The notification's second paragraph when all of the new wallet's sensors are
# disabled: Home Assistant's own word for enabling an entity, and the words
# the texts already use for sensors and a device page.
_SENSORS_DISABLED = {
    "en": "Its sensors are disabled. You can enable them on its [device page]({link}).",
    "de": "Seine Sensoren sind deaktiviert. Du kannst sie auf seiner [Geräteseite]({link}) "
    "aktivieren.",
    "fr": "Ses capteurs sont désactivés. Vous pouvez les activer sur sa [page d'appareil]({link}).",
    "nl": "De sensoren van deze wallet zijn uitgeschakeld. Je kunt ze inschakelen op de "
    "[apparaatpagina]({link}).",
    "it": "I suoi sensori sono disabilitati. Puoi abilitarli nella [pagina del dispositivo]({link}).",
    "es": "Sus sensores están deshabilitados. Puedes habilitarlos en su [página de dispositivo]"
    "({link}).",
    "pl": "Jego sensory są wyłączone. Możesz je włączyć na jego [stronie urządzenia]({link}).",
}


def test_the_sensors_disabled_hint_says_how_to_enable_them():
    """A paragraph of its own under the notification, linking to the same
    device page."""
    assert sorted(_SENSORS_DISABLED) == _LANGUAGES
    for language, hint in _SENSORS_DISABLED.items():
        exceptions = _load(f"translations/{language}.json")["exceptions"]
        assert exceptions["wallet_added_sensors_disabled"] == {"message": hint}, language


def test_the_setup_menu_says_what_each_service_is_for():
    """The setup menu names each service with nothing but its API key: the
    Portfolio needs one, the Price Tracker uses the Portfolio's. The text
    above it says what each one is for, as a list of its
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
            " you hold them or not. It uses the Portfolio's API key: set up the Portfolio first."
        ),
        "menu_options": {
            "portfolio": "Bitpanda Portfolio (API key required)",
            "price_tracker": "Bitpanda Price Tracker (uses the Portfolio's API key)",
        },
    }
    assert _load("translations/de.json")["config"]["step"]["user"] == {
        "title": "Bitpanda",
        "description": (
            "Welchen Dienst möchtest du einrichten? Jeder lässt sich einmal hinzufügen.\n\n"
            "- **Bitpanda Portfolio**: dein Konto \u2013 alles, was du bei Bitpanda hältst.\n"
            "- **Bitpanda Price Tracker**: Live-Preise der Assets, die du auswählst \u2013 auch"
            " ohne sie zu besitzen. Er nutzt den API-Schlüssel des Portfolios: Richte zuerst das"
            " Portfolio ein."
        ),
        "menu_options": {
            "portfolio": "Bitpanda Portfolio (API-Schlüssel benötigt)",
            "price_tracker": "Bitpanda Price Tracker (nutzt den API-Schlüssel des Portfolios)",
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
        assert permissions.startswith("2. ") and " \u2013 " not in permissions, name
        assert all(label in permissions for label in _PERMISSION_LABELS[_language(name)]), name
        assert paste.startswith("3. "), name
        assert len(key.split("\n")) == 4, name
    assert _load("strings.json")["config"]["step"]["portfolio"] == {
        "title": "Bitpanda Portfolio",
        "description": (
            "The Bitpanda Portfolio shows your Bitpanda account in Home Assistant: its total"
            " value, your returns, and a wallet for every asset you hold. The integration"
            " creates the wallets itself and removes them when you no longer hold an asset"
            " \u2013 you do not need to add or delete any.\n\n"
            "For this, the integration needs an API key. To create one:\n\n"
            "1. Open [{api_key_url}]({api_key_url}) and create a new API key.\n"
            '2. Select the permissions "Balances", "Transaction", "Earn (Read)" and'
            ' "Trade (Read)".\n'
            "3. Copy the API key and paste it below. Bitpanda shows it only once.\n\n"
            "The integration only reads with it: it cannot trade or move money.\n"
            "The Bitpanda Price Tracker uses the same API key.\n"
            "Bitpanda API keys are valid until the date you choose when creating them, one year at"
            " most; after that, Home Assistant asks for a new one.\n"
            'You can replace the API key at any time: open the ⋮ menu of the "Bitpanda Portfolio"'
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
            "1. Öffne [{api_key_url}]({api_key_url}) und erstelle einen neuen API-Schlüssel.\n"
            "2. Wähle die Berechtigungen „Guthaben“, „Transaktion“, „Earn (Read)“ und"
            " „Trading (Read)“.\n"
            "3. Kopiere den API-Schlüssel und füge ihn unten ein. Bitpanda zeigt ihn nur einmal"
            " an.\n\n"
            "Die Integration liest damit nur: Handeln oder Geld bewegen kann sie nicht.\n"
            "Der Bitpanda Price Tracker nutzt denselben API-Schlüssel.\n"
            "Bitpanda-API-Schlüssel gelten bis zu dem Datum, das du beim Erstellen wählst,"
            " höchstens ein Jahr; danach fragt Home Assistant nach einem neuen.\n"
            "Ersetzen kannst du den API-Schlüssel jederzeit: Öffne auf der"
            " Bitpanda-Integrationsseite das Menü ⋮ beim Eintrag „Bitpanda Portfolio“ und"
            " wähle „Neu konfigurieren“."
        ),
        "data": {"api_key": "API-Schlüssel"},
    }


def test_the_reconfigure_key_help_has_a_line_per_sentence():
    """Under Reconfigure's key field: that an empty field keeps the key; on
    a line of its own what a new key needs -- the four permissions, as in
    the setup's guide; and on a third, as in the setup, that the integration
    only reads with it. In the approved English and German wording."""
    help_texts = {
        name: _load(name)["config"]["step"]["reconfigure"]["data_description"]["api_key"]
        for name in _FILES
    }
    for name, help_text in help_texts.items():
        keep, new_key, reads = help_text.split("\n")
        setup_key = _load(name)["config"]["step"]["portfolio"]["description"].split("\n\n")[-1]
        assert reads == setup_key.split("\n")[0], name
        assert "[{api_key_url}]({api_key_url})" in new_key, name
        assert " \u2013 " not in new_key, name
        assert all(label in new_key for label in _PERMISSION_LABELS[_language(name)]), name
    assert help_texts["strings.json"] == (
        "Leave empty to keep the current API key.\n"
        'A new API key from [{api_key_url}]({api_key_url}) needs the permissions "Balances",'
        ' "Transaction", "Earn (Read)" and "Trade (Read)".\n'
        "The integration only reads with it: it cannot trade or move money."
    )
    assert help_texts["translations/de.json"] == (
        "Lass das Feld leer, um den aktuellen API-Schlüssel zu behalten.\n"
        "Ein neuer API-Schlüssel von [{api_key_url}]({api_key_url}) braucht die Berechtigungen"
        " „Guthaben“, „Transaktion“, „Earn (Read)“ und „Trading (Read)“.\n"
        "Die Integration liest damit nur: Handeln oder Geld bewegen kann sie nicht."
    )


def test_the_reauth_dialog_walks_through_creating_the_key_as_the_setup_does():
    """The new-key dialog says what happened and why; in a paragraph of its
    own that the sensors are kept and that the key must be of the same
    account; then, as the Portfolio's
    setup does, it walks through creating the
    key -- the same numbered steps -- and says that the integration only
    reads with it and how long a key is valid. Its field has no help text:
    the steps are the guide. In the approved English and German wording."""
    for name in _FILES:
        steps = _load(name)["config"]["step"]
        reauth = steps["reauth_confirm"]
        assert set(reauth) == {"title", "description", "data"}, name
        happened, kept, lead, guide, key = reauth["description"].split("\n\n")
        assert "\n" not in happened + kept + lead, name
        assert "{api_key_url}" not in happened + kept, name
        _, _, setup_guide, setup_key = steps["portfolio"]["description"].split("\n\n")
        assert guide == setup_guide, name
        assert key.split("\n") == setup_key.split("\n")[:3], name
    assert _load("strings.json")["config"]["step"]["reauth_confirm"]["description"] == (
        "Bitpanda rejected the stored API key. It may have expired, or it lacks a permission"
        " this version needs: since October 2026, Bitpanda gives prices only to an API key with"
        ' "Trade (Read)".\n\nYour sensors are kept. The new API key must belong'
        " to the same Bitpanda account. For another account, open the \u22ee menu of the"
        ' "Bitpanda Portfolio" entry on the Bitpanda integration page, choose "Delete" and set'
        " up the Portfolio again.\n\n"
        "To create a new API key:\n\n"
        "1. Open [{api_key_url}]({api_key_url}) and create a new API key.\n"
        '2. Select the permissions "Balances", "Transaction", "Earn (Read)" and'
        ' "Trade (Read)".\n'
        "3. Copy the API key and paste it below. Bitpanda shows it only once.\n\n"
        "The integration only reads with it: it cannot trade or move money.\n"
        "The Bitpanda Price Tracker uses the same API key.\n"
        "Bitpanda API keys are valid until the date you choose when creating them, one year at"
        " most; after that, Home Assistant asks for a new one."
    )
    assert _load("translations/de.json")["config"]["step"]["reauth_confirm"]["description"] == (
        "Bitpanda hat den gespeicherten API-Schlüssel abgelehnt. Er ist vielleicht abgelaufen,"
        " oder ihm fehlt eine Berechtigung, die diese Version braucht: Seit Oktober 2026 gibt"
        " Bitpanda Preise nur noch für einen API-Schlüssel mit „Trading (Read)“ heraus.\n\nDeine"
        " Sensoren bleiben erhalten. Der neue API-Schlüssel muss zum selben Bitpanda-Konto"
        " gehören. Für ein anderes Konto öffne auf der Bitpanda-Integrationsseite das Menü"
        " \u22ee beim Eintrag „Bitpanda Portfolio“, wähle „Löschen“ und richte das Portfolio"
        " danach neu ein.\n\n"
        "So erstellst du einen neuen API-Schlüssel:\n\n"
        "1. Öffne [{api_key_url}]({api_key_url}) und erstelle einen neuen API-Schlüssel.\n"
        "2. Wähle die Berechtigungen „Guthaben“, „Transaktion“, „Earn (Read)“ und"
        " „Trading (Read)“.\n"
        "3. Kopiere den API-Schlüssel und füge ihn unten ein. Bitpanda zeigt ihn nur einmal"
        " an.\n\n"
        "Die Integration liest damit nur: Handeln oder Geld bewegen kann sie nicht.\n"
        "Der Bitpanda Price Tracker nutzt denselben API-Schlüssel.\n"
        "Bitpanda-API-Schlüssel gelten bis zu dem Datum, das du beim Erstellen wählst,"
        " höchstens ein Jahr; danach fragt Home Assistant nach einem neuen."
    )


# The switch from a date version to 2.0.0, by the word each language gives
# it, and the word for an ordinary update, which the switch is never called:
# an update is any new version, also one within 2.x.
_SWITCH_WORDS = {
    "de": ("umstieg", "aktualisierung"),
    "en": ("upgrade", None),
    "es": ("migración", "actualización"),
    "fr": ("migration", "mise à jour"),
    "it": ("migrazione", "aggiornamento"),
    "nl": ("overstap", "update"),
    "pl": ("migracj", "aktualizac"),
}


def test_the_waiting_upgrades_texts_call_the_switch_by_its_own_word():
    """What the user sees while the upgrade waits for a new key -- why its
    setup failed, why a device stays, why the menu and Reconfigure wait --
    names the switch by its own word, never an update's."""
    for language, (switch, update) in _SWITCH_WORDS.items():
        strings = _load(f"translations/{language}.json")
        for text in (
            strings["exceptions"]["upgrade_key_needed"]["message"],
            strings["exceptions"]["upgrade_device_not_removable"]["message"],
            strings["config"]["abort"]["upgrade_pending"],
        ):
            assert switch in text.lower(), (language, text)
            if update is not None:
                assert update not in text.lower(), (language, text)


def test_the_upgrade_issues_call_the_switch_by_its_own_word():
    """Every repair issue about the switch from a date version names it in
    its title, by the same word, and none calls it an update -- "update
    Home Assistant" stays what it is."""
    assert sorted(_SWITCH_WORDS) == _LANGUAGES
    for language, (switch, update) in _SWITCH_WORDS.items():
        issues = _load(f"translations/{language}.json")["issues"]
        for key in (*migration.UPGRADE_ISSUES, *migration.BLOCKER_ISSUES):
            issue = issues[key]
            text = issue.get("description") or issue["fix_flow"]["step"]["confirm"]["description"]
            assert switch in issue["title"].lower(), (language, key)
            if update is not None:
                assert update not in (issue["title"] + text).lower(), (language, key)


def test_the_renamed_entity_ids_issue_says_why_the_ids_changed():
    """The entity IDs follow the device names, and every wallet and tracked
    asset got a device of its own: that -- not the two services -- is why
    they changed. In the approved English and German wording."""
    assert _load("strings.json")["issues"]["renamed_entities"]["description"] == (
        'The upgrade split the devices "Bitpanda Wallets" and "Bitpanda Price Tracker": each'
        " wallet and each tracked asset now has a device of its own, named after the asset."
        ' The figures of your account are on the "Portfolio" device. Entity IDs follow the'
        " device names, so these IDs were renamed; their history moved with them. Check"
        " dashboards, automations and scripts that still use the old IDs:\n\n{entities}"
    )
    assert _load("translations/de.json")["issues"]["renamed_entities"] == {
        "title": "Bitpanda-Umstieg: Entitäts-IDs umbenannt",
        "description": (
            "Beim Umstieg wurden die Geräte „Bitpanda Wallets“ und „Bitpanda Price Tracker“"
            " aufgeteilt: Jedes Wallet und jedes verfolgte Asset hat jetzt ein eigenes Gerät,"
            " benannt nach dem Asset. Gesamtwert, Bargeld und Renditen deines Kontos liegen"
            " beim Gerät „Portfolio“. Entitäts-IDs folgen den Gerätenamen, daher wurden diese"
            " IDs umbenannt; ihr Verlauf ist mitgewandert. Prüfe Dashboards, Automationen und"
            " Skripte, die noch die alten IDs verwenden:\n\n{entities}"
        ),
    }


def test_the_old_statistics_step_explains_its_three_choices():
    """The setup's question about old statistics: what happened, in one
    paragraph with both currencies; then a list item per button, led by the
    button's own label in bold -- the first two set up the Portfolio in the
    new currency, the second links Troubleshooting through a placeholder, as
    hassfest allows no URL in a text, and the third, Cancel, sets up and
    deletes nothing. Cancelling ends with a text of its own. In the approved
    English and German wording."""
    for name in _FILES:
        config = _load(name)["config"]
        step = config["step"]["old_statistics"]
        assert set(step) == {"title", "description", "menu_options"}, name
        assert set(step["menu_options"]) == {
            "delete_statistics", "keep_statistics", "cancel_setup"
        }, name
        intro, choices = step["description"].split("\n\n")
        assert "\n" not in intro and _placeholders(intro) == {"old", "new"}, name
        delete, keep, cancel = choices.split("\n")
        for item, option, placeholders in (
            (delete, "delete_statistics", {"new"}),
            (keep, "keep_statistics", {"new", "troubleshooting_url"}),
            (cancel, "cancel_setup", set()),
        ):
            label = re.escape(step["menu_options"][option])
            assert re.match(rf"- \*\*{label}\s?:\*\* ", item), (name, option)
            assert _placeholders(item) == placeholders, (name, option)
        assert _LINK_TARGET.findall(intro + delete + cancel) == [], name
        assert _LINK_TARGET.findall(keep) == ["{troubleshooting_url}"], name
        # The link text is the README's heading, in English in every file.
        assert "[Troubleshooting]({troubleshooting_url})" in keep, name
        assert _placeholders(config["abort"]["setup_cancelled"]) == set(), name
    english = _load("strings.json")["config"]
    assert english["step"]["old_statistics"] == {
        "title": "Old statistics in another currency",
        "description": (
            "Home Assistant still holds long-term statistics of an earlier Bitpanda Portfolio"
            " in {old}. You chose {new} for this setup. A sensor whose statistics are in another"
            " currency records no new statistics until the old ones are gone.\n\n"
            "- **Delete and set up:** deletes the history and long-term statistics of every"
            " earlier Portfolio sensor – figures, returns and wallets – and sets up the"
            " Portfolio in {new}. Its statistics then start afresh. The deleted data cannot be"
            " restored.\n"
            "- **Keep and set up:** sets up the Portfolio in {new} and deletes nothing. The"
            " sensors with old statistics then record no statistics at all, not even in {new},"
            " until you delete the old statistics yourself;"
            " [Troubleshooting]({troubleshooting_url}) in the README explains how.\n"
            "- **Cancel:** sets up and deletes nothing, for example to choose another currency."
        ),
        "menu_options": {
            "delete_statistics": "Delete and set up",
            "keep_statistics": "Keep and set up",
            "cancel_setup": "Cancel",
        },
    }
    assert english["abort"]["setup_cancelled"] == (
        "The Portfolio was not set up, and nothing was deleted."
    )
    german = _load("translations/de.json")["config"]
    assert german["step"]["old_statistics"] == {
        "title": "Alte Statistiken in anderer Währung",
        "description": (
            "Home Assistant hat noch Langzeitstatistiken eines früheren Bitpanda Portfolios in"
            " {old}. Du hast bei dieser Einrichtung {new} ausgewählt. Ein Sensor, dessen"
            " Statistik in einer anderen Währung vorliegt, zeichnet keine neue Statistik auf,"
            " bis die alte weg ist.\n\n"
            "- **Löschen und einrichten:** löscht Verlauf und Langzeitstatistiken aller"
            " früheren Portfolio-Sensoren – Kennzahlen, Renditen und Wallets – und richtet"
            " das Portfolio in {new} ein. Seine Statistik beginnt dann neu. Die gelöschten"
            " Daten lassen sich nicht wiederherstellen.\n"
            "- **Behalten und einrichten:** richtet das Portfolio in {new} ein und löscht"
            " nichts. Die Sensoren mit alter Statistik zeichnen dann gar keine Statistik mehr"
            " auf, auch nicht in {new}, bis du die alte Statistik selbst löschst;"
            " [Troubleshooting]({troubleshooting_url}) in der README erklärt, wie.\n"
            "- **Abbrechen:** richtet nichts ein und löscht nichts, zum Beispiel um eine andere"
            " Währung zu wählen."
        ),
        "menu_options": {
            "delete_statistics": "Löschen und einrichten",
            "keep_statistics": "Behalten und einrichten",
            "cancel_setup": "Abbrechen",
        },
    }
    assert german["abort"]["setup_cancelled"] == (
        "Das Portfolio wurde nicht eingerichtet, und es wurde nichts gelöscht."
    )


def test_the_currency_change_offers_its_choices():
    """Reconfigure's currency change asks before it deletes anything: the
    text says what the change does, and the buttons offer the change, the
    new API key alone when one was entered, and Cancel. In the approved
    English and German wording."""
    for name in _FILES:
        step = _load(name)["config"]["step"]["confirm_currency"]
        assert set(step) == {"title", "description", "menu_options"}, name
        assert set(step["menu_options"]) == {
            "change_currency", "change_key_and_currency", "save_key_only",
            "cancel_currency_change",
        }, name
        assert "\n" not in step["description"], name
        assert _placeholders(step["description"]) == {"old", "new"}, name
    english = _load("strings.json")["config"]["step"]["confirm_currency"]
    assert english["description"] == (
        "Changing the currency from {old} to {new} deletes all Portfolio sensors including"
        " their history and recreates them in the new currency. The deleted history cannot be"
        " restored; the currency itself can be changed again at any time."
    )
    assert english["menu_options"] == {
        "change_currency": "Change currency",
        "change_key_and_currency": "Save the new API key and change the currency",
        "save_key_only": "Save only the new API key",
        "cancel_currency_change": "Cancel",
    }
    german = _load("translations/de.json")["config"]["step"]["confirm_currency"]
    assert german["description"] == (
        "Wenn du die Währung von {old} auf {new} änderst, werden alle Portfolio-Sensoren"
        " samt Verlauf gelöscht und in der neuen Währung neu angelegt. Der gelöschte Verlauf"
        " lässt sich nicht wiederherstellen; die Währung selbst kannst du später jederzeit"
        " wieder ändern."
    )
    assert german["menu_options"] == {
        "change_currency": "Währung ändern",
        "change_key_and_currency": "Neuen API-Schlüssel speichern und Währung ändern",
        "save_key_only": "Nur den neuen API-Schlüssel speichern",
        "cancel_currency_change": "Abbrechen",
    }


# The key Bitpanda issues is called the API key everywhere -- never just the
# key -- so that no text leaves open which key is meant.
_BARE_KEY = {
    "de": r"(?<!API-)Schlüssel",
    "en": r"(?<!API )\bkeys?\b",
    "es": r"\bclaves?\b(?! API)",
    "fr": r"\bclés?\b(?! API)",
    "it": r"\bchiav[ei]\b(?! API)",
    "nl": r"(?<!API-)sleutel",
    "pl": r"\bklucz\w*\b(?! API)",
}


def test_every_text_calls_the_key_an_api_key():
    assert sorted(_BARE_KEY) == _LANGUAGES
    for name in _FILES:
        pattern = re.compile(_BARE_KEY[_language(name)], re.IGNORECASE)
        for key, text in _texts(_load(name)).items():
            assert not pattern.search(text), (name, key, text)


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
    """The error names the key's four permissions as Bitpanda's key page
    does in each language, each followed by the mark the code fills in --
    ✓ or ✗, never a word -- and asks for a new key with all four. In the
    approved English and German wording."""
    assert sorted(_PERMISSION_LABELS) == _LANGUAGES
    for name in _FILES:
        error = _load(name)["config"]["error"]["missing_scopes"]
        labels = _PERMISSION_LABELS[_language(name)]
        assert _placeholders(error) == set(REQUIRED_SCOPES), name
        assert len(labels) == len(REQUIRED_SCOPES), name
        for label, scope in zip(labels, REQUIRED_SCOPES, strict=True):
            assert f"{label} {{{scope}}}" in error, name
    assert _load("strings.json")["config"]["error"]["missing_scopes"] == (
        'Permissions of this API key: "Balances" {balance}, "Transaction" {transaction},'
        ' "Earn (Read)" {earn}, "Trade (Read)" {trading}. Permissions cannot be added to an'
        " existing API key. Create a new one with all four."
    )
    assert _load("translations/de.json")["config"]["error"]["missing_scopes"] == (
        "Berechtigungen dieses API-Schlüssels: „Guthaben“ {balance}, „Transaktion“"
        " {transaction}, „Earn (Read)“ {earn}, „Trading (Read)“ {trading}. Einem bestehenden"
        " API-Schlüssel lassen sich keine Berechtigungen hinzufügen. Erstelle einen neuen mit"
        " allen vieren."
    )


def test_the_rejected_key_error_names_the_likely_causes_and_the_permissions():
    """Bitpanda answers a wrong, deleted or expired key and a key with none of
    the four permissions alike: every probe of the setup fails. The error
    names these causes and the four permissions as Bitpanda's key page does
    in each language, and asks to check the key or create a new one with all
    four. In the approved English and German wording."""
    for name in _FILES:
        error = _load(name)["config"]["error"]["invalid_auth"]
        assert all(label in error for label in _PERMISSION_LABELS[_language(name)]), name
        assert _placeholders(error) == set(), name
    assert _load("strings.json")["config"]["error"]["invalid_auth"] == (
        "Bitpanda rejected this API key. It may be copied incompletely, deleted in your"
        " Bitpanda account or expired, or it has none of the permissions \"Balances\","
        " \"Transaction\", \"Earn (Read)\" and \"Trade (Read)\". Check the API key, or create a"
        " new one with all four."
    )
    assert _load("translations/de.json")["config"]["error"]["invalid_auth"] == (
        "Bitpanda hat diesen API-Schlüssel abgelehnt. Vielleicht ist er unvollständig"
        " kopiert, in deinem Bitpanda-Konto gelöscht oder abgelaufen, oder er hat keine der"
        " Berechtigungen „Guthaben“, „Transaktion“, „Earn (Read)“ und „Trading (Read)“. Prüfe"
        " den API-Schlüssel oder erstelle einen neuen mit allen vieren."
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


# A word that makes a following "Wallet" feminine, or a singular one
# masculine: "die Wallet", "eine neue Wallet", "der Wallet".
_FEMININE_WALLET = re.compile(
    r"\b(?:die|der|eine|einer|keine|keiner|diese|dieser|jede|jeder|deine|deiner"
    r"|ihre|ihrer|seine|seiner)\s+(?:\w+\s+)?Wallet\b",
    re.IGNORECASE,
)


_LIST_ITEM = re.compile(r"(?:- |\d+\. )")


def test_every_list_opens_a_paragraph_of_its_own():
    """A list -- bullets or numbered steps -- follows a blank line or
    another of its items, so that every Markdown renderer shows it as a
    list, not as a line of the paragraph before."""
    for name in _FILES:
        for key, text in _texts(_load(name)).items():
            lines = text.split("\n")
            for before, line in zip(lines, lines[1:]):
                if _LIST_ITEM.match(line):
                    assert before == "" or _LIST_ITEM.match(before), (name, key, line[:40])


def test_german_texts_say_das_wallet():
    """German texts treat a wallet as neuter, "das Wallet", as the
    Portfolio's setup ("ein eigenes Wallet") and the refusal to delete a
    held asset's wallet ("dieses Wallet") do; "die Wallets" is the plural."""
    feminine = [
        (key, match.group())
        for key, text in _texts(_load("translations/de.json")).items()
        for match in _FEMININE_WALLET.finditer(text)
    ]
    assert feminine == []


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
    fetches -- both services, or the one picked --, that the call waits for
    it, that a service within its cooldown is skipped and that a failed
    refresh fails the call -- in English and German."""
    assert _load("strings.json")["services"]["refresh"]["description"] == (
        "Fetches the portfolio and the prices from Bitpanda now, or only the chosen service, "
        "and waits until it is done. A service within its cooldown is skipped; fails when a "
        "refresh fails."
    )
    assert _load("translations/de.json")["services"]["refresh"]["description"] == (
        "Holt Portfolio und Preise sofort, oder nur den gewählten Dienst, und wartet, bis es "
        "fertig ist. Ein Dienst innerhalb seiner Sperrzeit wird übersprungen; schlägt fehl, "
        "wenn eine Aktualisierung fehlschlägt."
    )
    field = _load("translations/de.json")["services"]["refresh"]["fields"]["config_entry_id"]
    assert field["name"] == "Dienst"


# The steps whose field has no help text: the Portfolio's setup and the
# new-key dialog, whose step text above the key field is the guide to
# creating the key.
_WITHOUT_HELP_TEXT = {"config.portfolio", "config.reauth_confirm"}


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
    assert len(labelled) == 15
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
    upgrade's reports, what blocks the upgrade, and the Price Tracker's
    missing Portfolio. Each module's own tests render its issues in every
    language."""
    assert set(_load("strings.json")["issues"]) == {
        *migration.UPGRADE_ISSUES,
        *migration.BLOCKER_ISSUES,
        *PRICE_TRACKER_ISSUES,
    }


def test_the_menus_portfolio_required_names_the_way_to_the_portfolios_setup():
    """Choosing the Price Tracker while Bitpanda has no entry at all -- no
    integration page exists then -- says to set up the Portfolio first, by
    the way to it as three numbered steps: "Add integration", the search,
    then the menu's own Portfolio option, quoted as the same file labels
    it."""
    for name in _FILES:
        strings = _load(name)
        abort = strings["config"]["abort"]["portfolio_required"]
        assert _quoted(strings["config"]["step"]["user"]["menu_options"]["portfolio"]).search(abort), name
        _, steps = abort.split("\n\n")
        assert [line[:3] for line in steps.split("\n")] == ["1. ", "2. ", "3. "], name
    assert _load("translations/de.json")["config"]["abort"]["portfolio_required"] == (
        "Der Bitpanda Price Tracker nutzt den API-Schlüssel von Bitpanda Portfolio. Richte"
        " zuerst Bitpanda Portfolio ein:\n\n"
        "1. Wähle unter „Einstellungen“ → „Geräte & Dienste“ „Integration hinzufügen“.\n"
        "2. Suche nach Bitpanda.\n"
        "3. Wähle „Bitpanda Portfolio (API-Schlüssel benötigt)“."
    )


def test_a_refused_key_in_add_price_tracker_names_the_permission_and_the_dialog():
    """"Add price tracker" refused for the key: the permission it needs, as
    Bitpanda's key page names it, and where to enter a new key -- the
    new-key dialog by its own title in the same file."""
    for name in _FILES:
        strings = _load(name)
        error = strings["config_subentries"]["price_group"]["error"]["key_rejected"]
        assert _PERMISSION_LABELS[_language(name)][-1] in error, name
        assert _quoted(strings["config"]["step"]["reauth_confirm"]["title"]).search(error), name
    assert _load("translations/de.json")["config_subentries"]["price_group"]["error"]["key_rejected"] == (
        "Bitpanda hat den API-Schlüssel von Bitpanda Portfolio für Preise abgelehnt: Er braucht"
        " die Berechtigung „Trading (Read)“. Gib bei Bitpanda Portfolio unter „Neuer"
        " Bitpanda-API-Schlüssel nötig“ einen neuen API-Schlüssel ein."
    )


def test_the_portfolio_required_issue_says_why_and_what_to_do():
    """A Price Tracker without a Portfolio: why it shows no prices, what to
    set up -- with the four permissions as Bitpanda's key page names them in
    each language -- and that its price trackers stay. In the approved
    English and German wording; German calls the tracked assets by the
    integration's own word, „Preis-Tracker“. Short paragraphs, the way to
    fix it in bold, and the permissions as a list of their own in every
    language: the repair dialog shows one block of text otherwise."""
    assert_issue_texts_render({"portfolio_required": None})
    for name in _FILES:
        description = _load(name)["issues"]["portfolio_required"]["description"]
        labels = _PERMISSION_LABELS[_language(name)]
        assert "\n\n" + "\n".join(f"- {label}" for label in labels) + "\n\n" in description, name
        assert description.count("\n\n") == 3 and description.count("**") == 2, name
    english = _load("strings.json")["issues"]["portfolio_required"]
    assert english == {
        "title": "Bitpanda Price Tracker: set up Bitpanda Portfolio",
        "description": (
            "Since October 2026, Bitpanda gives prices only with an API key. The Price Tracker"
            " uses the API key of Bitpanda Portfolio, so it shows no prices without one.\n\n"
            '**To fix this:** set up Bitpanda Portfolio \u2013 "Add service" on the Bitpanda'
            " integration page. Its API key needs these four permissions:\n\n"
            '- "Balances"\n- "Transaction"\n- "Earn (Read)"\n- "Trade (Read)"\n\n'
            "Your price trackers stay as they are and show prices again once the Portfolio is"
            " set up."
        ),
    }
    assert _load("translations/de.json")["issues"]["portfolio_required"] == {
        "title": "Bitpanda Price Tracker: Bitpanda Portfolio einrichten",
        "description": (
            "Seit Oktober 2026 gibt Bitpanda Preise nur noch mit einem API-Schlüssel heraus. Der"
            " Price Tracker nutzt den API-Schlüssel von Bitpanda Portfolio und zeigt ohne ihn keine"
            " Preise.\n\n"
            "**So behebst du es:** Richte Bitpanda Portfolio ein \u2013 „Dienst hinzufügen“ auf der"
            " Bitpanda-Integrationsseite. Der API-Schlüssel braucht diese vier Berechtigungen:\n\n"
            "- „Guthaben“\n- „Transaktion“\n- „Earn (Read)“\n- „Trading (Read)“\n\n"
            "Deine Preis-Tracker bleiben, wie sie sind, und zeigen wieder Preise, sobald das"
            " Portfolio eingerichtet ist."
        ),
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
        "return_month", "return_six_month", "return_year", "invested", "total_return",
        "total_return_percent", "value_crypto", "value_stock", "value_etf", "value_etc",
        "value_index", "value_metal", "value_other", "staking", "wallet_total", "wallet",
        "price",
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
    assert set(group["abort"]) == {"already_configured", "asset_added", "portfolio_required"}
    assert "{asset}" in group["abort"]["asset_added"]
    assert "{group}" in group["abort"]["asset_added"]
    assert set(group["create_entry"]) == {"default"}


def test_a_new_group_and_a_joined_one_end_with_the_same_text():
    """The first asset of a type starts its group, every later one joins
    it: both dialogs end with the same message, naming asset and group."""
    for name in _FILES:
        group = _load(name)["config_subentries"]["price_group"]
        assert group["create_entry"]["default"] == group["abort"]["asset_added"], name


# The asset type step's hint: how long a large list takes the first time
# (measured: about 12 seconds for Bitpanda's stocks).
_CATEGORY_HINT = {
    "de": "Der nächste Schritt zeigt alle Assets dieses Typs, die du noch nicht verfolgst. "
    "Große Listen wie Aktien brauchen beim ersten Öffnen bis zu einer halben Minute.",
    "en": "The next step lists every asset of this type that you do not track yet. "
    "Large lists such as stocks take up to half a minute to load the first time.",
    "es": "El siguiente paso muestra todos los activos de este tipo que aún no sigues. "
    "Las listas grandes, como las acciones, tardan hasta medio minuto en cargarse la primera vez.",
    "fr": "L'étape suivante liste tous les actifs de ce type que vous ne suivez pas encore. "
    "Les grandes listes, comme les actions, mettent jusqu'à une demi-minute à se charger "
    "la première fois.",
    "it": "Il passaggio successivo elenca tutti gli asset di questo tipo che non monitori ancora. "
    "Gli elenchi grandi, come le azioni, impiegano fino a mezzo minuto a caricarsi la prima volta.",
    "nl": "De volgende stap toont alle assets van dit type die je nog niet volgt. "
    "Grote lijsten zoals aandelen laden de eerste keer tot een halve minuut.",
    "pl": "Następny krok pokaże wszystkie aktywa tego rodzaju, których jeszcze nie śledzisz. "
    "Duże listy, takie jak akcje, wczytują się za pierwszym razem do pół minuty.",
}


def test_the_asset_type_hint_says_how_long_a_large_list_takes():
    assert sorted(_CATEGORY_HINT) == _LANGUAGES
    for language, hint in _CATEGORY_HINT.items():
        step = _load(f"translations/{language}.json")["config_subentries"]["price_group"]["step"]
        assert step["user"]["data_description"]["category"] == hint, language


def test_the_german_reauth_title_joins_the_compound_with_hyphens():
    config = _load("translations/de.json")["config"]
    assert config["step"]["reauth_confirm"]["title"] == "Neuer Bitpanda-API-Schlüssel nötig"


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


class _TickerPrices:
    """Every wallet's ticker price, 2.0, as WalletPrices gives it."""

    def price_of(self, asset_id):
        return 2.0

    def async_listen(self, asset_id, update):
        return lambda: None


def _with_a_day_ago(sensor):
    """`sensor` once its price of 24 hours ago is known."""
    sensor.set_price_24h_ago(1.0)
    return sensor


def _attribute_scenarios() -> list[tuple[str, dict]]:
    """(translation_key, published attributes) for every sensor class that
    publishes attributes. A translation_key may appear more than once, when
    different sensor states publish different, mutually exclusive attributes
    (PriceSensor's `conversion` vs. `conversion_rate`/`rate_date`/
    `rate_source`, depending on whether an ECB rate has loaded yet) -- the
    test unions every scenario sharing a key before comparing it to that
    key's labels, so this still proves each one has a label."""
    wallet_coordinator = _Coordinator(_wallet_portfolio_data())
    # The last payout a day ago: within the last 30 days.
    last_at = (dt_util.utcnow() - timedelta(days=1)).isoformat()
    rewards = _Coordinator({_VSN["id"]: RewardTotals(
        gross=12.0, fee=2.4, net=9.6, count=3, last_at=last_at,
        payouts=(RewardPayout(last_at, 4.0, 0.8, 3.2),),
    )})
    earn = _Coordinator(EarnData(
        apr={_VSN["id"]: 0.0544}, offered=frozenset({_VSN["id"]}),
        products={_VSN["id"]: EarnProduct(
            apr=0.0544, type="FLEXIBLE", mode="STAKING_EARN", sold_out=False, enabled=True
        )},
    ))

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
                wallet_coordinator, earn, rewards, "eid", "EUR", asset, _TickerPrices()
            ).extra_state_attributes),
            ("wallet_total", WalletTotalSensor(
                wallet_coordinator, "eid", "EUR", asset
            ).extra_state_attributes),
            ("wallet_total", _with_a_day_ago(WalletTotalSensor(
                wallet_coordinator, "eid", "EUR", asset, prices=_TickerPrices()
            )).extra_state_attributes),
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
        *(
            (f"return_{timeframe.lower()}", PortfolioReturnSensor(
                _Coordinator(PortfolioReturns(values={timeframe: 1.25})), "eid", timeframe,
                wallet_coordinator,
            ).extra_state_attributes)
            for timeframe in ("DAY", "WEEK", "MONTH", "SIX_MONTH", "YEAR")
        ),
        *(
            (sensor_class._key, sensor_class(
                wallet_coordinator, "eid", "EUR"
            ).extra_state_attributes)
            for sensor_class in (
                PortfolioInvestedSensor, PortfolioTotalReturnSensor,
                PortfolioTotalReturnPercentSensor,
            )
        ),
        *(
            (f"value_{category}", PortfolioClassSensor(
                wallet_coordinator, "eid", "EUR", category, lambda: [_VSN["id"], _ETF["id"]],
            ).extra_state_attributes)
            for category in ASSET_CATEGORIES
        ),
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


# The rewards of the last 30 days and of the last payout on the Staking
# sensor, by language: quantities and today's values named as the lifetime
# ones are, French with a no-break space before the colon and after the 30.
_RECENT_REWARD_LABELS = {
    "de": {
        "rewards_net_30d": "Belohnungen: netto, letzte 30 Tage (Menge)",
        "rewards_net_value_30d": "Belohnungen: Wert netto, letzte 30 Tage (aktuell)",
        "rewards_last_net": "Belohnungen: letzte Gutschrift, netto (Menge)",
        "rewards_last_value": "Belohnungen: letzte Gutschrift, Wert (aktuell)",
    },
    "en": {
        "rewards_net_30d": "Rewards: net, last 30 days (quantity)",
        "rewards_net_value_30d": "Rewards: net value, last 30 days (current)",
        "rewards_last_net": "Rewards: last payout, net (quantity)",
        "rewards_last_value": "Rewards: last payout, value (current)",
    },
    "es": {
        "rewards_net_30d": "Recompensas: neto, últimos 30 días (cantidad)",
        "rewards_net_value_30d": "Recompensas: valor neto, últimos 30 días (actual)",
        "rewards_last_net": "Recompensas: último pago, neto (cantidad)",
        "rewards_last_value": "Recompensas: último pago, valor (actual)",
    },
    "fr": {
        "rewards_net_30d": "Récompenses\u00a0: net, 30\u00a0derniers jours (quantité)",
        "rewards_net_value_30d": "Récompenses\u00a0: valeur nette, 30\u00a0derniers jours (actuelle)",
        "rewards_last_net": "Récompenses\u00a0: dernier versement, net (quantité)",
        "rewards_last_value": "Récompenses\u00a0: dernier versement, valeur (actuelle)",
    },
    "it": {
        "rewards_net_30d": "Ricompense: netto, ultimi 30 giorni (quantità)",
        "rewards_net_value_30d": "Ricompense: valore netto, ultimi 30 giorni (attuale)",
        "rewards_last_net": "Ricompense: ultimo accredito, netto (quantità)",
        "rewards_last_value": "Ricompense: ultimo accredito, valore (attuale)",
    },
    "nl": {
        "rewards_net_30d": "Beloningen: netto, laatste 30 dagen (hoeveelheid)",
        "rewards_net_value_30d": "Beloningen: nettowaarde, laatste 30 dagen (actueel)",
        "rewards_last_net": "Beloningen: laatste uitbetaling, netto (hoeveelheid)",
        "rewards_last_value": "Beloningen: laatste uitbetaling, waarde (actueel)",
    },
    "pl": {
        "rewards_net_30d": "Nagrody: netto, ostatnie 30 dni (ilość)",
        "rewards_net_value_30d": "Nagrody: wartość netto, ostatnie 30 dni (bieżąca)",
        "rewards_last_net": "Nagrody: ostatnie naliczenie, netto (ilość)",
        "rewards_last_value": "Nagrody: ostatnie naliczenie, wartość (bieżąca)",
    },
}


def test_the_recent_rewards_are_named_like_the_lifetime_ones():
    assert sorted(_RECENT_REWARD_LABELS) == _LANGUAGES
    for language, labels in _RECENT_REWARD_LABELS.items():
        attributes = _load(f"translations/{language}.json")["entity"]["sensor"]["staking"][
            "state_attributes"
        ]
        assert {key: attributes[key]["name"] for key in labels} == labels, language
        prefix = attributes["rewards_net"]["name"].split(":", 1)[0]
        quantity = attributes["rewards_net"]["name"].rsplit("(", 1)[1]
        current = attributes["rewards_net_value"]["name"].rsplit("(", 1)[1]
        for key, label in labels.items():
            assert label.split(":", 1)[0] == prefix, (language, key)
            suffix = current if "value" in key else quantity
            assert label.endswith(f"({suffix}"), (language, key)


# The position performance on a wallet's Total sensor, by language, in the
# order of _POSITION_KEYS. French puts a no-break space before the colon and
# the percent sign.
_POSITION_KEYS = ("average_buy_price", "invested_amount", "total_return", "total_return_percent")
_POSITION_LABELS = {
    "de": (
        "Bilanz: Ø Kaufpreis", "Bilanz: investiert", "Bilanz: Gesamtrendite",
        "Bilanz: Gesamtrendite %",
    ),
    "en": (
        "Position: average buy price", "Position: invested", "Position: total return",
        "Position: total return %",
    ),
    "es": (
        "Posición: precio medio de compra", "Posición: importe invertido",
        "Posición: rentabilidad total", "Posición: rentabilidad total %",
    ),
    "fr": (
        "Position\u00a0: prix d'achat moyen", "Position\u00a0: montant investi",
        "Position\u00a0: rendement total", "Position\u00a0: rendement total en\u00a0%",
    ),
    "it": (
        "Posizione: prezzo medio di acquisto", "Posizione: importo investito",
        "Posizione: rendimento totale", "Posizione: rendimento totale %",
    ),
    "nl": (
        "Positie: gemiddelde aankoopprijs", "Positie: geïnvesteerd bedrag",
        "Positie: totaalrendement", "Positie: totaalrendement %",
    ),
    "pl": (
        "Pozycja: średnia cena zakupu", "Pozycja: zainwestowana kwota",
        "Pozycja: całkowity zwrot", "Pozycja: całkowity zwrot %",
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


# The asset's price and the 24 hours on a wallet's Total sensor, by
# language: the price under the asset's prefix, the 24 hours under the
# prefix the Price Tracker uses, its two keys named as there.
_WALLET_PRICE_LABELS = {
    "de": {"price": "Asset: Preis", "return_24h": "24 h: Rendite"},
    "en": {"price": "Asset: price", "return_24h": "24 h: return"},
    "es": {"price": "Activo: precio", "return_24h": "24 h: rentabilidad"},
    "fr": {"price": "Actif\u00a0: prix", "return_24h": "24\u00a0h\u00a0: rendement"},
    "it": {"price": "Asset: prezzo", "return_24h": "24 h: rendimento"},
    "nl": {"price": "Asset: prijs", "return_24h": "24 uur: rendement"},
    "pl": {"price": "Aktywo: cena", "return_24h": "24 h: zwrot"},
}


def test_a_wallets_price_and_24_hours_are_named_like_the_price_trackers():
    assert sorted(_WALLET_PRICE_LABELS) == _LANGUAGES
    for language, labels in _WALLET_PRICE_LABELS.items():
        sensors = _load(f"translations/{language}.json")["entity"]["sensor"]
        total = sensors["wallet_total"]["state_attributes"]
        price = sensors["price"]["state_attributes"]
        assert {key: total[key]["name"] for key in labels} == labels, language
        for key in ("price_24h_ago", "change_24h_pct"):
            assert total[key]["name"] == price[key]["name"], (language, key)
        assert labels["price"].split(":", 1)[0] == total["asset"]["name"].split(":", 1)[0], language
    german = _load("translations/de.json")["entity"]["sensor"]["wallet_total"]["state_attributes"]
    assert (german["price_24h_ago"]["name"], german["change_24h_pct"]["name"]) == (
        "24 h: Preis davor", "24 h: Änderung %",
    )


# The value of each wallet group, by language: the word for "value", then
# the group's title as setup names the groups, in the case the language
# writes it mid-sentence -- French with a no-break space before the colon.
_CLASS_NAMES = {
    "de": ("Wert: Kryptowährungen", "Wert: Aktien", "Wert: ETFs", "Wert: ETCs",
           "Wert: Krypto-Indizes", "Wert: Edelmetalle", "Wert: Sonstige"),
    "en": ("Value: cryptocurrencies", "Value: stocks", "Value: ETFs", "Value: ETCs",
           "Value: crypto indices", "Value: precious metals", "Value: other"),
    "es": ("Valor: criptomonedas", "Valor: acciones", "Valor: ETF", "Valor: ETC",
           "Valor: índices cripto", "Valor: metales preciosos", "Valor: otros"),
    "fr": ("Valeur\u00a0: cryptomonnaies", "Valeur\u00a0: actions", "Valeur\u00a0: ETF",
           "Valeur\u00a0: ETC", "Valeur\u00a0: indices crypto", "Valeur\u00a0: métaux précieux",
           "Valeur\u00a0: autres"),
    "it": ("Valore: criptovalute", "Valore: azioni", "Valore: ETF", "Valore: ETC",
           "Valore: indici cripto", "Valore: metalli preziosi", "Valore: altro"),
    "nl": ("Waarde: cryptovaluta", "Waarde: aandelen", "Waarde: ETF's", "Waarde: ETC's",
           "Waarde: crypto-indices", "Waarde: edelmetalen", "Waarde: overige"),
    "pl": ("Wartość: kryptowaluty", "Wartość: akcje", "Wartość: ETF", "Wartość: ETC",
           "Wartość: indeksy kryptowalut", "Wartość: metale szlachetne", "Wartość: inne"),
}


def test_each_groups_value_is_named_after_its_group():
    assert sorted(_CLASS_NAMES) == _LANGUAGES
    for language, names in _CLASS_NAMES.items():
        strings = _load(f"translations/{language}.json")
        sensors = strings["entity"]["sensor"]
        titles = strings["selector"]["asset_group"]["options"]
        assert tuple(sensors[f"value_{category}"]["name"] for category in ASSET_CATEGORIES) == (
            names
        ), language
        for category, name in zip(ASSET_CATEGORIES, names):
            group = name.split(":", 1)[1].strip()
            assert group.casefold() == titles[category].casefold(), (language, category)


# A group's figures, by language, under a prefix of their own; the money
# figures named as a wallet's position figures are.
_GROUP_KEYS = ("share_percent", "invested_amount", "total_return", "total_return_percent", "wallets")
_GROUP_LABELS = {
    "de": ("Gruppe: Anteil %", "Gruppe: investiert", "Gruppe: Gesamtrendite",
           "Gruppe: Gesamtrendite %", "Gruppe: Wallets"),
    "en": ("Group: share %", "Group: invested", "Group: total return", "Group: total return %",
           "Group: wallets"),
    "es": ("Grupo: participación %", "Grupo: importe invertido", "Grupo: rentabilidad total",
           "Grupo: rentabilidad total %", "Grupo: wallets"),
    "fr": ("Groupe\u00a0: part en\u00a0%", "Groupe\u00a0: montant investi", "Groupe\u00a0: rendement total",
           "Groupe\u00a0: rendement total en\u00a0%", "Groupe\u00a0: wallets"),
    "it": ("Gruppo: quota %", "Gruppo: importo investito", "Gruppo: rendimento totale",
           "Gruppo: rendimento totale %", "Gruppo: wallet"),
    "nl": ("Groep: aandeel %", "Groep: geïnvesteerd bedrag", "Groep: totaalrendement",
           "Groep: totaalrendement %", "Groep: wallets"),
    "pl": ("Grupa: udział %", "Grupa: zainwestowana kwota", "Grupa: całkowity zwrot",
           "Grupa: całkowity zwrot %", "Grupa: portfele"),
}

# A wallet's share of the portfolio, under its position figures' prefix.
_SHARE_LABELS = {
    "de": "Bilanz: Anteil am Portfolio %",
    "en": "Position: share of portfolio %",
    "es": "Posición: participación en el portfolio %",
    "fr": "Position\u00a0: part du portfolio en\u00a0%",
    "it": "Posizione: quota del portfolio %",
    "nl": "Positie: aandeel in portfolio %",
    "pl": "Pozycja: udział w portfolio %",
}


def test_a_groups_figures_are_named_like_a_positions():
    assert sorted(_GROUP_LABELS) == sorted(_SHARE_LABELS) == _LANGUAGES
    for language, labels in _GROUP_LABELS.items():
        sensors = _load(f"translations/{language}.json")["entity"]["sensor"]
        position = sensors["wallet_total"]["state_attributes"]
        for category in ASSET_CATEGORIES:
            attributes = sensors[f"value_{category}"]["state_attributes"]
            assert tuple(attributes[key]["name"] for key in _GROUP_KEYS) == labels, language
        for key, label in zip(_GROUP_KEYS[1:4], labels[1:4]):
            assert label.split(":", 1)[1] == position[key]["name"].split(":", 1)[1], (language, key)
        share = position["portfolio_share_percent"]["name"]
        assert share == _SHARE_LABELS[language], language
        assert share.split(":", 1)[0] == position["invested_amount"]["name"].split(":", 1)[0]


# The Portfolio's event entities: their names, and the names of their event
# types, in English and German.
_EVENT_NAMES = {
    "en": {
        "new_wallet": ("New wallet", {"wallet_added": "Wallet added"}),
        "staking_reward": ("Staking reward", {"staking_reward_received": "Staking reward received"}),
        "earn_change": ("Earn change", {
            "offered": "Offered", "withdrawn": "Withdrawn", "sold_out": "Sold out",
            "available_again": "Available again", "apr": "APR changed",
        }),
    },
    "de": {
        "new_wallet": ("Neues Wallet", {"wallet_added": "Wallet angelegt"}),
        "staking_reward": ("Staking-Belohnung", {"staking_reward_received": "Staking-Belohnung erhalten"}),
        "earn_change": ("Earn-Änderung", {
            "offered": "Angeboten", "withdrawn": "Nicht mehr angeboten", "sold_out": "Ausverkauft",
            "available_again": "Wieder verfügbar", "apr": "Zinssatz (APR) geändert",
        }),
    },
}


def test_each_event_entity_and_event_type_has_a_name():
    """Every language names the three entities and every event type of
    theirs; English and German as approved."""
    for language in _LANGUAGES:
        events = _load(f"translations/{language}.json")["entity"]["event"]
        assert set(events) == set(PORTFOLIO_EVENT_TYPES), language
        for key, types in PORTFOLIO_EVENT_TYPES.items():
            assert events[key]["name"], (language, key)
            assert set(events[key]["state_attributes"]["event_type"]["state"]) == set(types), (
                language, key,
            )
    for language, names in _EVENT_NAMES.items():
        events = _load(f"translations/{language}.json")["entity"]["event"]
        for key, (name, types) in names.items():
            assert events[key]["name"] == name, (language, key)
            assert events[key]["state_attributes"]["event_type"]["state"] == types, (language, key)


def test_every_field_an_event_entity_shows_has_a_label():
    """Each announcement's fields are the entity's attributes: every one is
    labelled, in every language, and nothing else is."""
    strings = _load("strings.json")["entity"]["event"]
    for key, fields in ANNOUNCEMENT_FIELDS.items():
        labels = set(strings[key]["state_attributes"]) - {"event_type"}
        assert labels == fields, key
    for language in _LANGUAGES:
        events = _load(f"translations/{language}.json")["entity"]["event"]
        for key in PORTFOLIO_EVENT_TYPES:
            assert set(events[key]["state_attributes"]) == set(strings[key]["state_attributes"]), (
                language, key,
            )
            for attribute, label in events[key]["state_attributes"].items():
                if attribute != "event_type":
                    assert label["name"], (language, key, attribute)


def test_an_event_entitys_asset_fields_are_labelled_like_a_wallets():
    """Symbol, name and category as on Balance (total), in every language."""
    for language in _LANGUAGES:
        sensors = _load(f"translations/{language}.json")["entity"]
        total = sensors["sensor"]["wallet_total"]["state_attributes"]
        for key in ("new_wallet", "staking_reward"):
            attributes = sensors["event"][key]["state_attributes"]
            for field, attribute in (("symbol", "asset"), ("name", "asset_name")):
                assert attributes[field]["name"] == total[attribute]["name"], (language, key)
        assert sensors["event"]["new_wallet"]["state_attributes"]["category"]["name"] == (
            total["asset_category"]["name"]
        ), language


# The Earn attributes of the Staking sensor, in English and German, with the
# names of their values.
_EARN_LABELS = {
    "en": {
        "earn_type": ("Earn: type", {"flexible": "Flexible", "locked": "Locked"}),
        "earn_mode": ("Earn: mode", {"staking": "Staking", "stable_coin": "Stablecoin"}),
        "earn_sold_out": ("Earn: sold out", None),
    },
    "de": {
        "earn_type": ("Earn: Typ", {"flexible": "Flexibel", "locked": "Gebunden"}),
        "earn_mode": ("Earn: Modus", {"staking": "Staking", "stable_coin": "Stablecoin"}),
        "earn_sold_out": ("Earn: ausverkauft", None),
    },
}


def test_the_earn_attributes_and_their_values_are_named():
    for language in _LANGUAGES:
        attributes = _load(f"translations/{language}.json")["entity"]["sensor"]["staking"][
            "state_attributes"
        ]
        assert set(attributes["earn_type"]["state"]) == {"flexible", "locked"}, language
        assert set(attributes["earn_mode"]["state"]) == {"staking", "stable_coin"}, language
    for language, labels in _EARN_LABELS.items():
        attributes = _load(f"translations/{language}.json")["entity"]["sensor"]["staking"][
            "state_attributes"
        ]
        for key, (name, states) in labels.items():
            assert attributes[key]["name"] == name, (language, key)
            assert attributes[key].get("state") == states, (language, key)


# The Portfolio's actions with response data, in English and German.
_ACTION_NAMES = {
    "en": {
        "get_portfolio": "Get portfolio",
        "get_portfolio_history": "Get portfolio history",
        "get_staking_rewards": "Get staking rewards",
    },
    "de": {
        "get_portfolio": "Portfolio abrufen",
        "get_portfolio_history": "Portfolio-Verlauf abrufen",
        "get_staking_rewards": "Staking-Belohnungen abrufen",
    },
}


def test_every_action_and_field_is_named_and_described():
    """Each action services.yaml declares, and each of its fields, has a
    name and a description in every language; the timeframes are named."""
    import yaml

    declared = yaml.safe_load((_DIR / "services.yaml").read_text(encoding="utf-8"))
    timeframes = declared["get_portfolio_history"]["fields"]["timeframe"]["selector"]["select"]
    for language in _LANGUAGES:
        texts = _load(f"translations/{language}.json")
        assert set(texts["services"]) == set(declared), language
        for name, service in declared.items():
            assert texts["services"][name]["name"] and texts["services"][name]["description"]
            fields = (service or {}).get("fields", {})
            assert set(texts["services"][name].get("fields", {})) == set(fields), (language, name)
            for field in texts["services"][name].get("fields", {}).values():
                assert field["name"] and field["description"], (language, name)
        assert set(texts["selector"][timeframes["translation_key"]]["options"]) == set(
            timeframes["options"]
        ), language
        for key in ("no_portfolio", "portfolio_unavailable", "rewards_start_after_end"):
            assert texts["exceptions"][key]["message"], (language, key)
    for language, names in _ACTION_NAMES.items():
        services = _load(f"translations/{language}.json")["services"]
        assert {name: services[name]["name"] for name in names} == names, language


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


def test_the_category_attribute_is_labelled_like_the_other_asset_attributes():
    """The approved names of `asset_category` in each language, on every sensor
    that carries the other asset attributes."""
    labels = {
        "en": "Asset: category", "de": "Asset: Kategorie", "fr": "Actif : catégorie",
        "nl": "Asset: categorie", "it": "Asset: categoria", "es": "Activo: categoría",
        "pl": "Aktywo: kategoria",
    }
    assert sorted(labels) == _LANGUAGES
    for name in _FILES:
        language = "en" if name == "strings.json" else Path(name).stem
        sensors = _load(name)["entity"]["sensor"]
        for key in ("wallet", "wallet_total", "staking", "price"):
            attribute = sensors[key]["state_attributes"]["asset_category"]
            assert attribute == {"name": labels[language]}, (name, key)


# Bitpanda's API does not tell which account a key belongs to: the key dialogs
# say that a new key must be of the same account, and that another account
# means deleting the Portfolio and setting it up again (approved 2026-10-14).
# The new-key dialog says it in its first paragraph, Reconfigure after its own
# line.
_SAME_ACCOUNT = {
    "de": (
        "Der neue API-Schlüssel muss zum selben Bitpanda-Konto gehören.",
        "Ein neuer API-Schlüssel muss zum selben Bitpanda-Konto gehören.",
        " Für ein anderes Konto öffne auf der Bitpanda-Integrationsseite das Menü ⋮ beim Eintrag "
        "„Bitpanda Portfolio“, wähle „Löschen“ und richte das Portfolio danach neu ein.",
    ),
    "en": (
        "The new API key must belong to the same Bitpanda account.",
        "A new API key must belong to the same Bitpanda account.",
        " For another account, open the ⋮ menu of the \"Bitpanda Portfolio\" entry on the Bitpanda "
        "integration page, choose \"Delete\" and set up the Portfolio again.",
    ),
    "es": (
        "La nueva clave API debe pertenecer a la misma cuenta de Bitpanda.",
        "Una nueva clave API debe pertenecer a la misma cuenta de Bitpanda.",
        " Para otra cuenta, abre el menú ⋮ de la entrada \"Bitpanda Portfolio\" en la página de la "
        "integración Bitpanda, elige \"Eliminar\" y vuelve a configurar el Portfolio.",
    ),
    "fr": (
        "La nouvelle clé API doit appartenir au même compte Bitpanda.",
        "Une nouvelle clé API doit appartenir au même compte Bitpanda.",
        " Pour un autre compte, ouvrez le menu ⋮ de l'entrée «\u00a0Bitpanda Portfolio\u00a0» sur la page de "
        "l'intégration Bitpanda, choisissez «\u00a0Supprimer\u00a0» puis configurez à nouveau le Portfolio.",
    ),
    "it": (
        "La nuova chiave API deve appartenere allo stesso account Bitpanda.",
        "Una nuova chiave API deve appartenere allo stesso account Bitpanda.",
        " Per un altro account apri il menu ⋮ della voce \"Bitpanda Portfolio\" nella pagina "
        "dell'integrazione Bitpanda, scegli \"Elimina\" e configura di nuovo il Portfolio.",
    ),
    "nl": (
        "De nieuwe API-sleutel moet bij hetzelfde Bitpanda-account horen.",
        "Een nieuwe API-sleutel moet bij hetzelfde Bitpanda-account horen.",
        " Voor een ander account open je op de integratiepagina van Bitpanda het menu ⋮ bij de invoer "
        "\"Bitpanda Portfolio\", kies je \"Verwijderen\" en stel je het Portfolio daarna opnieuw in.",
    ),
    "pl": (
        "Nowy klucz API musi należeć do tego samego konta Bitpanda.",
        "Nowy klucz API musi należeć do tego samego konta Bitpanda.",
        " Aby użyć innego konta, otwórz na stronie integracji Bitpanda menu ⋮ przy wpisie "
        "„Bitpanda Portfolio”, wybierz „Usuń” i skonfiguruj Portfolio od nowa.",
    ),
}


def test_reconfigure_says_the_price_tracker_uses_the_same_key():
    """Reconfigure says, after what it changes, that the Bitpanda Price
    Tracker uses the same API key -- ending the first paragraph; the
    same-account sentence follows in a paragraph of its own. In the approved
    English and German wording."""
    for name in _FILES:
        description = _load(name)["config"]["step"]["reconfigure"]["description"]
        uses = _load(name)["config"]["step"]["portfolio"]["description"].split("\n\n")[-1]
        assert f". {uses.split(chr(10))[1]}\n\n" in description, name
    assert _load("strings.json")["config"]["step"]["reconfigure"]["description"].startswith(
        "Replace the stored API key, change the currency, or both. The Bitpanda Price Tracker"
        " uses the same API key.\n\nA new API key must belong to the same Bitpanda account."
    )
    assert _load("translations/de.json")["config"]["step"]["reconfigure"]["description"].startswith(
        "Ersetze den gespeicherten API-Schlüssel, ändere die Währung oder beides. Der Bitpanda"
        " Price Tracker nutzt denselben API-Schlüssel.\n\nEin neuer API-Schlüssel muss zum selben"
        " Bitpanda-Konto gehören."
    )


def test_the_key_dialogs_say_a_new_key_must_be_of_the_same_account():
    """Both dialogs that take a new key -- the new-key dialog
    (reauth_confirm), at the end of its second paragraph, and Reconfigure, in
    a paragraph of its own that ends its description -- say that the key must belong to the same
    Bitpanda account, and how to switch to another one: delete the Portfolio
    and set it up again."""
    assert sorted(_SAME_ACCOUNT) == _LANGUAGES
    for language, (reauth, reconfigure, another) in _SAME_ACCOUNT.items():
        step = _load(f"translations/{language}.json")["config"]["step"]
        kept = step["reauth_confirm"]["description"].split("\n\n")[1]
        assert kept.endswith(f" {reauth}{another}"), language
        assert step["reconfigure"]["description"].endswith(f"\n\n{reconfigure}{another}"), language


def test_the_setups_end_with_the_way_to_the_cards():
    """Both setups end by saying where the Bitpanda cards are and how to put
    one on a dashboard; the Price Tracker's first how to add assets. The
    English and German wording, word for word."""
    way = {
        "en": (
            'open the dashboard, select "Edit dashboard" (✏ at the top right; on a phone in the ⋮ '
            'menu), then "Add card" and the "By card" tab, and search for "Bitpanda". If no '
            'Bitpanda card is listed, reload the page twice; in the Home Assistant app, '
            '[reset its frontend cache]({cards_url}) instead.\n\nThe new "Overview", the default of '
            'new installations since Home Assistant 2026.2, takes no cards: first create a dashboard under "Settings" → '
            '"Dashboards" → "Add dashboard".'
        ),
        "de": (
            "Öffne das Dashboard, wähle „Dashboard bearbeiten“ (✏ oben rechts, auf dem Handy im "
            "⋮-Menü), dann „Karte hinzufügen“ und den Reiter „Nach Karte“, und suche nach "
            "„Bitpanda“. Erscheint keine Bitpanda-Karte, lade die Seite zweimal neu; in der "
            "Home-Assistant-App [setze stattdessen ihren Frontend-Cache zurück]({cards_url}).\n\n"
            "Die neue „Übersicht“, seit Home Assistant 2026.2 der Standard neuer Installationen, nimmt keine Karten auf: Lege zuerst unter "
            "„Einstellungen“ → „Dashboards“ → „Dashboard hinzufügen“ ein eigenes Dashboard an."
        ),
    }
    expected = {
        "en": {
            "portfolio": 'To see your portfolio on a dashboard, add the "Bitpanda Portfolio" card: '
            + way["en"],
            "price_tracker": 'Add the assets you want to track with "Add price tracker" on the '
            '"Bitpanda Price Tracker" entry of the Bitpanda integration page. Then add the '
            '"Bitpanda Price Tracker" card to a dashboard: ' + way["en"],
        },
        "de": {
            "portfolio": "Um dein Portfolio auf einem Dashboard zu sehen, füge ihm die Karte "
            "„Bitpanda Portfolio“ hinzu: " + way["de"],
            "price_tracker": "Füge die gewünschten Assets mit „Preis-Tracker hinzufügen“ beim "
            "Eintrag „Bitpanda Price Tracker“ auf der Bitpanda-Integrationsseite hinzu. Füge "
            "danach einem Dashboard die Karte „Bitpanda Price Tracker“ hinzu: " + way["de"],
        },
    }
    for language, texts in expected.items():
        assert _load(f"translations/{language}.json")["config"]["create_entry"] == texts, language
    assert _load("strings.json")["config"]["create_entry"] == expected["en"]
    # Every language: both texts, each naming its card.
    for language in _LANGUAGES:
        endings = _load(f"translations/{language}.json")["config"]["create_entry"]
        assert set(endings) == {"portfolio", "price_tracker"}, language
        assert "Bitpanda Portfolio" in endings["portfolio"], language
        assert endings["price_tracker"].count("Bitpanda Price Tracker") == 2, language


def test_the_closing_texts_send_the_app_to_the_readmes_card_section():
    """Reloading does not help in the Home Assistant app: both closing texts
    link the README's card section, which says what does, in every language."""
    for language in _LANGUAGES:
        endings = _load(f"translations/{language}.json")["config"]["create_entry"]
        for key, text in endings.items():
            assert re.search(r"\]\(\{cards_url\}\)", text), (language, key)
            # The Overview's sentence stands in a paragraph of its own.
            assert "\n\n" in text, (language, key)


def test_no_text_carries_the_emoji_variation_selector():
    """A symbol in a text stands as it is ("✏", "⚙"): never with U+FE0F, which
    some fonts draw as a coloured emoji in the middle of a sentence."""
    for name in _FILES:
        path = _DIR / name
        assert "\ufe0f" not in path.read_text(encoding="utf-8"), name


def test_french_keeps_its_no_break_spaces():
    """French typography, as everywhere in fr.json: a
    no-break space (U+00A0) inside « » and before a colon or a semicolon, so
    that no line starts with » or a colon. A plain space there slips in
    easily when a text is edited."""
    text = (_DIR / "translations/fr.json").read_text(encoding="utf-8")
    for plain in ("« ", " »", " :", " ;"):
        assert plain not in text, repr(plain)
