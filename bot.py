import requests
import os
from datetime import datetime

# GitHub Secrets-ből olvassa be
BOT_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

# ──────────────────────────────────────────
#   PORTFÓLIÓ KONFIGURÁCIÓ
#   Coin ID (CoinGecko szerinti) -> mennyiség
# ──────────────────────────────────────────
portfolio = {
    'bitcoin':  0.5,
    'ethereum': 2.0,
    'solana':   10.0,
    # 'cardano': 500,
    # 'ripple':  300,
}

# Emoji az egyes coinokhoz (opcionális, ismeretlen coinhoz 🪙 kerül)
COIN_EMOJI = {
    'bitcoin':  '₿',
    'ethereum': '⟠',
    'solana':   '◎',
    'cardano':  '₳',
    'ripple':   '✕',
    'dogecoin': 'Ð',
    'litecoin': 'Ł',
}

# ──────────────────────────────────────────

def get_prices(coin_ids: list[str]) -> dict:
    """Egyszerre kéri le az összes coin árát, csökkentve az API hívások számát."""
    ids_param = ','.join(coin_ids)
    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={ids_param}&vs_currencies=usd&include_24hr_change=true"
    )
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def format_change(change: float) -> str:
    """Formázza a 24h változást nyíllal és előjellel."""
    arrow = '📈' if change >= 0 else '📉'
    sign  = '+' if change >= 0 else ''
    return f"{arrow} {sign}{change:.2f}%"

def format_number(value: float) -> str:
    """Ezres elválasztóval formázza az USD összeget."""
    return f"{value:,.2f}"

def send_telegram_msg(text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    CHAT_ID,
        "text":       text,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()

def build_message(portfolio: dict, prices: dict) -> str:
    now   = datetime.utcnow().strftime('%Y-%m-%d  %H:%M UTC')
    lines = []

    lines.append("╔═══════════════════════════╗")
    lines.append("║   🚀  CRYPTO  JELENTÉS    ║")
    lines.append("╚═══════════════════════════╝")
    lines.append(f"🕐 <i>{now}</i>")
    lines.append("")
    lines.append("┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄")

    total_usd = 0.0

    for coin, amount in portfolio.items():
        if coin not in prices:
            lines.append(f"⚠️  <b>{coin.capitalize()}</b> – ár nem elérhető")
            continue

        price_data = prices[coin]
        price      = price_data.get('usd', 0)
        change_24h = price_data.get('usd_24h_change', 0)
        value      = price * amount
        total_usd += value

        emoji = COIN_EMOJI.get(coin, '🪙')
        lines.append(
            f"{emoji} <b>{coin.capitalize()}</b>\n"
            f"   Ár:       <code>${format_number(price)}</code>\n"
            f"   Mennyiség: <code>{amount:g}</code>\n"
            f"   Érték:    <code>${format_number(value)}</code>\n"
            f"   24h:      {format_change(change_24h)}"
        )
        lines.append("┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄")

    lines.append(f"\n💼 <b>Portfólió összérték</b>")
    lines.append(f"   <code>${format_number(total_usd)}</code>")
    lines.append("\n<i>Adatok forrása: CoinGecko</i>")

    return '\n'.join(lines)


if __name__ == '__main__':
    coin_ids = list(portfolio.keys())
    prices   = get_prices(coin_ids)
    message  = build_message(portfolio, prices)
    send_telegram_msg(message)
    print("✅ Üzenet elküldve!")
    print(message)
