#!/usr/bin/env python3
"""
Crypto Portfolio Telegram Reporter v2.0
Küld egy formázott üzenetet a Telegram boton keresztül a CoinGecko API-ból lekérdezett
kriptovaluta árak alapján.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

# ----------------------------- KONFIGURÁCIÓ ---------------------------------

# Alapértelmezett JSON fájl neve a portfólió adatokhoz
DEFAULT_PORTFOLIO_FILE = "portfolio.json"

# Környezeti változók (GitHub Secrets vagy lokális .env)
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

# Logolás beállítása
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Coin nevek szépítése (display name)
COIN_NAMES: Dict[str, str] = {
    "bitcoin": "Bitcoin",
    "ethereum": "Ethereum",
    "solana": "Solana",
    "binancecoin": "Binance Coin",
    "cardano": "Cardano",
    "ripple": "XRP",
    "dogecoin": "Dogecoin",
    "polkadot": "Polkadot",
    # További coinok hozzáadhatók
}


# ----------------------------- SAJÁT KIVÉTEL ---------------------------------
class CryptoReporterError(Exception):
    """Általános kivétel a Crypto Reporter számára."""

    pass


# ----------------------------- SEGÉDFÜGGVÉNYEK ---------------------------------
def load_portfolio(file_path: str = DEFAULT_PORTFOLIO_FILE) -> Dict[str, float]:
    """
    Betölti a portfóliót egy JSON fájlból.
    A JSON formátuma: {"coin_id": mennyiség, ...}
    Példa: {"bitcoin": 0.01854, "ethereum": 1.0185}
    """
    if not os.path.exists(file_path):
        raise CryptoReporterError(
            f"A portfólió fájl nem található: {file_path}. "
            "Hozz létre egy 'portfolio.json' fájlt a fenti formátumban."
        )
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            portfolio = json.load(f)
        # Ellenőrizzük, hogy minden érték szám
        for coin, amount in portfolio.items():
            if not isinstance(amount, (int, float)):
                raise CryptoReporterError(
                    f"'{coin}' mennyisége nem szám: {amount}"
                )
        return portfolio
    except json.JSONDecodeError as e:
        raise CryptoReporterError(f"JSON hiba a {file_path} fájlban: {e}")


def get_prices(coin_ids: List[str]) -> Dict[str, Dict]:
    """
    Lekéri az aktuális árakat a CoinGecko API-ról (USD, HUF és 24h változás).
    """
    ids_param = ",".join(coin_ids)
    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={ids_param}&vs_currencies=usd,huf&include_24hr_change=true"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Ellenőrizzük, hogy minden kért coin megérkezett
        missing = [c for c in coin_ids if c not in data]
        if missing:
            logger.warning(f"A következő coinok nem találhatók az API válaszában: {missing}")
        return data
    except requests.exceptions.RequestException as e:
        raise CryptoReporterError(f"CoinGecko API hiba: {e}")


def format_usd(value: float) -> str:
    """Dollár formázása ezres elválasztóval, két tizedesjegy."""
    return f"${value:,.2f}"


def format_huf(value: float) -> str:
    """Forint formázása szóközös ezres elválasztóval (pl. 1 000 000 Ft)."""
    return f"{value:,.0f}".replace(",", " ") + " Ft"


def format_change(change_24h: Optional[float]) -> Tuple[str, str, str]:
    """
    A 24 órás változás alapján visszaadja a színes pöttyöt, a trend ikont és a formázott szöveget.
    Ha a változás None, akkor "n/a" és semleges ikonok.
    """
    if change_24h is None:
        return "⚪", "❓", "n/a"
    if change_24h >= 0:
        return "🟢", "📈", f"+{change_24h:.2f}%"
    else:
        return "🔴", "📉", f"{change_24h:.2f}%"


def build_message(portfolio: Dict[str, float], prices: Dict[str, Dict]) -> str:
    """Összeállítja a Telegram üzenetet HTML formátumban."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "🚀 <b>NAPI CRYPTO JELENTÉS</b>",
        f"🕒 <i>{now}</i>",
        "",
    ]

    total_usd = 0.0
    total_huf = 0.0

    for coin, amount in portfolio.items():
        # Szép név megjelenítése
        display_name = COIN_NAMES.get(coin, coin.replace("_", " ").title())

        if coin not in prices:
            lines.append(f"⚠️ <b>{display_name}</b> – ár nem elérhető\n")
            continue

        price_data = prices[coin]
        price_usd = price_data.get("usd", 0.0)
        price_huf = price_data.get("huf", 0.0)
        change_24h = price_data.get("usd_24h_change")  # lehet None

        value_usd = price_usd * amount
        value_huf = price_huf * amount
        total_usd += value_usd
        total_huf += value_huf

        color_dot, trend, change_str = format_change(change_24h)

        lines.append(f"🪙 <b>Kriptovaluta:</b> {display_name}")
        lines.append(
            f"💰 <b>Ár:</b> {color_dot} {format_usd(price_usd)}  |  {format_huf(price_huf)}"
        )
        lines.append(f"⚖️ <b>Mennyiség:</b> {amount:g}")
        lines.append(
            f"💵 <b>Érték:</b> {color_dot} {format_usd(value_usd)}  |  {format_huf(value_huf)}"
        )
        lines.append(f"📊 <b>24h változás:</b> {trend} {change_str}")
        lines.append("")  # üres sor a blokkok elválasztásához

    # Összesítő szekció
    lines.append("💼 <b>PORTFÓLIÓ ÖSSZÉRTÉK</b>")
    lines.append(f"🇺🇸 <b>USD:</b> {format_usd(total_usd)}")
    lines.append(f"🇭🇺 <b>HUF:</b> {format_huf(total_huf)}")
    lines.append("")
    lines.append(
        "🔗 <i>Adatok forrása: <a href='https://www.coingecko.com/'>CoinGecko</a></i>"
    )

    return "\n".join(lines)


def send_telegram_msg(text: str) -> None:
    """Elküldi az üzenetet a Telegram boton keresztül."""
    if len(text) > 4000:
        logger.warning(
            f"Az üzenet hossza ({len(text)} karakter) megközelíti a Telegram 4096 karakteres limitjét."
            " Lehet, hogy csonkolódni fog."
        )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise CryptoReporterError(f"Telegram üzenet küldés sikertelen: {e}")


# ----------------------------- MAIN ---------------------------------
def main() -> None:
    """Fő belépési pont."""
    # Környezeti változók ellenőrzése
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TOKEN":
        raise CryptoReporterError(
            "A TELEGRAM_TOKEN környezeti változó nincs beállítva vagy helytelen."
        )
    if not CHAT_ID or CHAT_ID == "YOUR_CHAT_ID":
        raise CryptoReporterError(
            "A CHAT_ID környezeti változó nincs beállítva vagy helytelen."
        )

    # Portfólió betöltése
    portfolio = load_portfolio()
    logger.info(f"Portfólió betöltve: {len(portfolio)} coin")

    # Árak lekérése
    coin_ids = list(portfolio.keys())
    prices = get_prices(coin_ids)
    logger.info(f"Árak lekérve {len(prices)} coinról")

    # Üzenet összeállítása és elküldése
    message = build_message(portfolio, prices)
    send_telegram_msg(message)
    logger.info("Üzenet sikeresen elküldve")
    # Konzolra is kiírjuk ellenőrzésképp (ha scriptből futtatják)
    print(message)


if __name__ == "__main__":
    try:
        main()
    except CryptoReporterError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Váratlan hiba: {e}")
        sys.exit(1)
