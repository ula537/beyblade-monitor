import requests
from bs4 import BeautifulSoup
import time
import json
import os
from urllib.parse import urljoin
from flask import Flask
import threading

print("程式啟動")

# ================= 設定 =================

TOKEN = "8183572724:AAGThEkMATxo_g4zsShkF0oImzRv3UK_WOc"
CHAT_ID = "8806826310"

CHECK_TIME = 60
SAVE_FILE = "seen.json"

SOURCES = [
    {
        "name": "Funbox",
        "url": "https://shop.funbox.com.tw/collections/%E6%88%B0%E9%AC%A5%E9%99%80%E8%9E%BA"
    }
]

# ================= Telegram =================

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
        print("Telegram錯誤:", e)

# ================= seen.json =================

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

# ================= 庫存 =================

def check_stock(text):

    no_stock = [
        "售罄",
        "缺貨",
        "暫時缺貨",
        "補貨中",
        "無庫存",
        "貨到通知"
    ]

    for word in no_stock:
        if word in text:
            return False

    return True

# ================= 抓商品 =================

def get_products():

    products = {}

    for site in SOURCES:

        print("=" * 50)
        print("掃描:", site["name"])

        try:

            print("開始抓網址")
            print(site["url"])

            r = requests.get(
                site["url"],
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
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

                text = a.get_text(
                    " ",
                    strip=True
                )

                href = a.get("href")

                if not href:
                    continue

                if "/products/" not in href:
                    continue

                if (
                    "BEYBLADE" not in text.upper()
                    and "戰鬥陀螺" not in text
                ):
                    continue

                if href.startswith("/"):

                    href = urljoin(
                        site["url"],
                        href
                    )

                key = site["name"] + "|" + href

                products[key] = {
                    "site": site["name"],
                    "name": text,
                    "url": href,
                    "stock": check_stock(text)
                }

                count += 1

                print(
                    "抓到:",
                    text[:80]
                )

            print(
                site["name"],
                "抓到商品:",
                count
            )

        except Exception as e:

            print("Funbox錯誤:", repr(e))

    return products

# ================= 監控 =================

def monitor():

    seen = load_seen()

    first_run = len(seen) == 0

    print("開始監控戰鬥陀螺")

    while True:

        products = get_products()

        print(
            time.strftime("%H:%M:%S"),
            "商品數:",
            len(products)
        )

        for key, p in products.items():

            site = p["site"]
            name = p["name"]
            url = p["url"]
            stock = p["stock"]

            if key not in seen:

                if not first_run:

                    msg = f"""🆕 新商品

來源:
{site}

商品:
{name}

🔗
{url}
"""

                    send_telegram(msg)

                seen[key] = p

            else:

                old_stock = seen[key].get(
                    "stock",
                    False
                )

                if old_stock is False and stock is True:

                    msg = f"""🔥 補貨通知

來源:
{site}

商品:
{name}

🔗
{url}
"""

                    send_telegram(msg)

                seen[key]["stock"] = stock

        save_seen(seen)

        first_run = False

        time.sleep(CHECK_TIME)

# ================= Flask =================

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