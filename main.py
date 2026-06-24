import requests
from bs4 import BeautifulSoup
import time
import json
import os
from urllib.parse import urljoin
from flask import Flask
import threading

print("版本20260624-1")
print("程式啟動")

TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

CHECK_TIME = 60

SAVE_FILE = "seen.json"

URL = "https://shop.funbox.com.tw/collections/%E6%88%B0%E9%AC%A5%E9%99%80%E8%9E%BA"


def send_telegram(msg):

    try:

        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=10
        )

    except Exception as e:

        print("Telegram錯誤", e)


def load_seen():

    if os.path.exists(SAVE_FILE):

        with open(
            SAVE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    return {}


def save_seen(data):

    with open(
        SAVE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


def get_products():

    products = {}

    print("=" * 50)
    print("掃描 Funbox")

    try:

        r = requests.get(
            URL,
            headers={
                "User-Agent":
                "Mozilla/5.0"
            },
            timeout=20
        )

        print("HTTP:", r.status_code)

        html = r.text

        print("HTML長度:", len(html))

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        count = 0

        for a in soup.find_all("a"):

            href = a.get("href")

            text = a.get_text(
                " ",
                strip=True
            )

            if not href:
                continue

            if "/products/" not in href:
                continue

            if (
                "戰鬥陀螺" not in text
                and
                "BEYBLADE" not in text.upper()
            ):
                continue

            if href.startswith("/"):

                href = urljoin(
                    URL,
                    href
                )

            key = href

            products[key] = {

                "name": text,
                "url": href

            }

            count += 1

            print("抓到:", text)

        print("商品數:", count)

    except Exception as e:

        print("錯誤:", e)

    return products


def monitor():

    seen = load_seen()

    first_run = len(seen) == 0

    while True:

        products = get_products()

        for key, p in products.items():

            if key not in seen:

                if not first_run:

                    msg = f"""
🆕 新商品

{p['name']}

{p['url']}
"""

                    send_telegram(msg)

                seen[key] = p

        save_seen(seen)

        first_run = False

        time.sleep(CHECK_TIME)


app = Flask(__name__)


@app.route("/")
def home():

    return "Beyblade Monitor Running"


threading.Thread(
    target=monitor,
    daemon=True
).start()


app.run(
    host="0.0.0.0",
    port=int(
        os.environ.get(
            "PORT",
            10000
        )
    )
)
