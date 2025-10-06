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
- Automatische Aktualisierung alle 5 Minuten
- Dynamische Nachkommastellen (zeigt präzise Werte auch für günstige Coins)

✅ **Wallet-Tracking**
- Überwache deine Crypto-Wallets (BTC, ETH, etc.)
- Verfolge Edelmetall-Bestände (Gold/XAU, Silber/XAG, Platin/XPT, Palladium/XPD)
- Tracke Bitpanda Index-Investments (BCI5, BCI10, etc.)
- Zeigt sowohl Menge als auch Wert in deiner gewählten Währung
- Automatische Aktualisierung alle 10 Minuten

✅ **Multi-Währung Support**
- EUR, USD, CHF, GBP und alle anderen von Bitpanda unterstützten Währungen

## Screenshots

*(Optional: Füge hier Screenshots deiner Integration ein)*

## Installation

### HACS (empfohlen)

1. Stelle sicher, dass [HACS](https://hacs.xyz/) installiert ist
2. Gehe zu HACS → Integrationen
3. Klicke auf die drei Punkte oben rechts → **Benutzerdefinierte Repositories**
4. Füge folgende URL hinzu: `https://github.com/DEIN_USERNAME/ha-bitpanda-integration`
5. Wähle als Kategorie: **Integration**
6. Klicke auf **Hinzufügen**
7. Suche nach "Bitpanda" in HACS und installiere die Integration
8. Starte Home Assistant neu

### Manuelle Installation

1. Lade die neueste Version aus den [Releases](https://github.com/DEIN_USERNAME/ha-bitpanda-integration/releases) herunter
2. Entpacke das Archiv
3. Kopiere den `custom_components/bitpanda` Ordner in dein Home Assistant `custom_components` Verzeichnis
4. Starte Home Assistant neu

## Einrichtung

### 1. Bitpanda API-Key erstellen

1. Logge dich in dein [Bitpanda-Konto](https://www.bit
