import requests
import os

# GitHub Secrets-ből fogjuk olvasni
BOT_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

def get_crypto_price(coin_id):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    response = requests.get(url).json()
    return response[coin_id]['usd']

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={text}"
    requests.get(url)

# Itt add meg a portfóliódat
portfolio = {'bitcoin': 0.5, 'ethereum': 2}
message = "Reggeli Crypto Jelentés:\n"
total = 0

for coin, amount in portfolio.items():
    price = get_crypto_price(coin)
    value = price * amount
    total += value
    message += f"{coin.capitalize()}: {value:.2f} USD\n"

message += f"\nÖsszesen: {total:.2f} USD"
send_telegram_msg(message)
