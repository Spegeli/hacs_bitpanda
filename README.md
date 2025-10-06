# Bitpanda Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/DEIN_USERNAME/ha-bitpanda-integration.svg)](https://github.com/DEIN_USERNAME/ha-bitpanda-integration/releases)
[![License](https://img.shields.io/github/license/DEIN_USERNAME/ha-bitpanda-integration.svg)](LICENSE)

Eine inoffizielle Home Assistant Integration für [Bitpanda](https://www.bitpanda.com), mit der du deine Krypto-, Edelmetall- und Index-Portfolios direkt in Home Assistant überwachen kannst.

> ⚠️ **Hinweis:** Diese Integration ist **nicht offiziell von Bitpanda** entwickelt oder unterstützt. Es handelt sich um ein Community-Projekt, das die öffentliche Bitpanda API verwendet.

## Features

✅ **Preis-Tracker**
- Verfolge Live-Preise von Kryptowährungen, Edelmetallen und Indizes
- Unterstützung für alle auf Bitpanda verfügbaren Assets
- Automatische Aktualisierung jede Minuten
- Dynamische Nachkommastellen (zeigt präzise Werte auch für günstige Coins)

✅ **Wallet-Tracking**
- Überwache deine Crypto-Wallets (BTC, ETH, etc.)
- Verfolge Edelmetall-Bestände (Gold/XAU, Silber/XAG, Platin/XPT, Palladium/XPD)
- Tracke Bitpanda Index-Investments (BCI5, BCI10, etc.)
- Zeigt sowohl Menge als auch Wert in deiner gewählten Währung
- Automatische Aktualisierung alle 5 Minuten

✅ **Multi-Währung Support**
- EUR, USD, CHF, GBP und alle anderen von Bitpanda unterstützten Währungen

## Screenshots

*(Optional: Füge hier Screenshots deiner Integration ein)*

## Installation

### HACS (empfohlen)

1. Stelle sicher, dass [HACS](https://hacs.xyz/) installiert ist
2. Gehe zu HACS → Integrationen
3. Klicke auf die drei Punkte oben rechts → **Benutzerdefinierte Repositories**
4. Füge folgende URL hinzu: `https://github.com/Spegeli/hacs_bitpanda`
5. Wähle als Kategorie: **Integration**
6. Klicke auf **Hinzufügen**
7. Suche nach "Bitpanda" in HACS und installiere die Integration
8. Starte Home Assistant neu

### Manuelle Installation

1. Lade die neueste Version aus den [Releases](https://github.com/Spegeli/hacs_bitpanda/releases) herunter
2. Entpacke das Archiv
3. Kopiere den `custom_components/bitpanda` Ordner in dein Home Assistant `custom_components` Verzeichnis
4. Starte Home Assistant neu

## Einrichtung

### 1. Bitpanda API-Key erstellen

1. Logge dich in dein [Bitpanda-Konto](https://www.bitpanda.com) ein
2. Gehe zu **Einstellungen** → **API**
3. Erstelle einen neuen API-Key mit **Lese-Berechtigung**
4. Kopiere den API-Key (du siehst ihn nur einmal!)

### 2. Integration in Home Assistant hinzufügen

1. Gehe zu **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
2. Suche nach "Bitpanda"
3. Gib deinen API-Key ein
4. Wähle deine bevorzugte Währung (z.B. EUR)
5. Klicke auf **Absenden**

### 3. Assets und Wallets konfigurieren

1. Gehe zur Bitpanda Integration
2. Klicke auf **Konfigurieren**
3. Wähle **Preis-Tracker** um Assets zu tracken
4. Wähle **Wallets** um deine Wallet-Bestände zu überwachen

## Verwendung

### Sensoren

Die Integration erstellt automatisch Sensoren für alle ausgewählten Assets und Wallets:

**Preis-Tracker Sensoren:**
