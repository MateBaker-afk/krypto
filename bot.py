import requests
import os
from datetime import datetime

# GitHub Secrets-ből olvassa be (lokális futtatásnál figyelj a beállításukra)
BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN', 'YOUR_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID', 'YOUR_CHAT_ID')

# ──────────────────────────────────────────
#   PORTFÓLIÓ KONFIGURÁCIÓ
# ──────────────────────────────────────────
portfolio = {
    'bitcoin':  0.01854176,
    'ethereum': 1.01853784,
    'solana':   0.548591298,
}

def get_prices(coin_ids: list[str]) -> dict:
    """Egyszerre kéri le az összes coin árát USD-ben és HUF-ban, csökkentve az API hívásokat."""
    ids_param = ','.join(coin_ids)
    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={ids_param}&vs_currencies=usd,huf&include_24hr_change=true"
    )
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def format_usd(value: float) -> str:
    """Dollár formázása ezres elválasztóval."""
    return f"${value:,.2f}"

def format_huf(value: float) -> str:
    """Forint formázása szóközös ezres elválasztóval (pl. 1 000 000 Ft)."""
    return f"{value:,.0f}".replace(',', ' ') + " Ft"

def send_telegram_msg(text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    CHAT_ID,
        "text":       text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()

def build_message(portfolio: dict, prices: dict) -> str:
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    lines = []

    # MBVK stílusú fejléc
    lines.append("🚀 <b>NAPI CRYPTO JELENTÉS</b>")
    lines.append(f"🕒 <i>{now}</i>")
    lines.append("")

    total_usd = 0.0
    total_huf = 0.0

    for coin, amount in portfolio.items():
        if coin not in prices:
            lines.append(f"⚠️ <b>{coin.capitalize()}</b> – ár nem elérhető\n")
            continue

        price_data = prices[coin]
        price_usd = price_data.get('usd', 0)
        price_huf = price_data.get('huf', 0)
        change_24h = price_data.get('usd_24h_change', 0)

        value_usd = price_usd * amount
        value_huf = price_huf * amount
        total_usd += value_usd
        total_huf += value_huf

        # Színek és irányok meghatározása a 24 órás változás alapján
        if change_24h >= 0:
            color_dot = "🟢"
            trend = "📈"
            sign = "+"
        else:
            color_dot = "🔴"
            trend = "📉"
            sign = ""

        # MBVK-hoz hasonló, tiszta listás elrendezés (nincs dobozolás)
        lines.append(f"🪙 <b>Kriptovaluta:</b> {coin.capitalize()}")
        lines.append(f"💰 <b>Ár:</b> {color_dot} {format_usd(price_usd)}  |  {format_huf(price_huf)}")
        lines.append(f"⚖️ <b>Mennyiség:</b> {amount:g}")
        lines.append(f"💵 <b>Érték:</b> {color_dot} {format_usd(value_usd)}  |  {format_huf(value_huf)}")
        lines.append(f"📊 <b>24h változás:</b> {trend} {sign}{change_24h:.2f}%")
        lines.append("")  # Üres sor a blokkok elválasztásához

    # Összesítő szekció
    lines.append("💼 <b>PORTFÓLIÓ ÖSSZÉRTÉK</b>")
    lines.append(f"🇺🇸 <b>USD:</b> {format_usd(total_usd)}")
    lines.append(f"🇭🇺 <b>HUF:</b> {format_huf(total_huf)}")
    lines.append("")
    lines.append("🔗 <i>Adatok forrása: CoinGecko</i>")

    return '\n'.join(lines)

if __name__ == '__main__':
    try:
        coin_ids = list(portfolio.keys())
        prices = get_prices(coin_ids)
        message = build_message(portfolio, prices)
        send_telegram_msg(message)
        print("✅ Üzenet sikeresen elküldve!")
        print(message) # Konzolra is kiírja ellenőrzésképp
    except Exception as e:
        print(f"❌ Hiba történt: {e}")
