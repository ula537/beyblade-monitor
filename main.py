import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import json
import os
from datetime import datetime
from urllib.parse import urljoin
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from flask import Flask
import threading
import traceback

print("程式啟動")
# =================設定=================

TOKEN=os.getenv("8183572724:AAEBnmAdXgGQBnoTXAW9GYz6GfxBlxqiJGU")
CHAT_ID=os.getenv("8806826310")

CHECK_TIME = 60

SAVE_FILE = "seen.json"


SOURCES = [

{
"name":"Funbox",
"url":"https://shop.funbox.com.tw/collections/%E6%88%B0%E9%AC%A5%E9%99%80%E8%9E%BA"
},

{
"name":"MOMO",
"url":"https://www.momoshop.com.tw/search/%E6%88%B0%E9%AC%A5%E9%99%80%E8%9E%BA?originalCateCode=2186500000&isBrandCategory=Y&_isFuzzy=2&searchType=1"
},

{
"name":"蝦皮商城",
"url":"https://shopee.tw/funbox5120"
},

{
"name":"誠品",
"url":"https://www.eslite.com/Search?keyword=%E6%88%B0%E9%AC%A5%E9%99%80%E8%9E%BA"
},

{
"name":"墊腳石",
"url":"https://www.tcsb.com.tw/v2/Search?q=%E6%88%B0%E9%AC%A5%E9%99%80%E8%9E%BA"
}

]


# =================Telegram=================

def send_telegram(msg):

    url=f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    try:

        requests.post(
            url,
            data={
                "chat_id":CHAT_ID,
                "text":msg
            },
            timeout=10
        )

    except Exception as e:
        print("Telegram錯誤",e)



# =================讀取=================

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



# =================Chrome=================

def selenium_html(url):

    opt=Options()

    opt.add_argument("--headless")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")
    opt.add_argument("--disable-gpu")
    opt.add_argument("--window-size=1920,1080")


    driver=webdriver.Chrome(
        service=Service(
            ChromeDriverManager().install()
        ),
        options=opt
    )


    driver.get(url)

    time.sleep(5)

    html=driver.page_source

    driver.quit()

    return html



# =================庫存=================

def check_stock(text):

    text=text.lower()


    no_stock=[

        "售罄",
        "缺貨",
        "暫時缺貨",
        "補貨中",
        "無庫存",
        "貨到通知"

    ]


    for x in no_stock:

        if x in text:

            return False


    return True



# =================抓商品=================

def get_products():

    products={}


    for site in SOURCES:


        print("\n掃描:",site["name"])


        try:


            if site["name"]=="Funbox":

                print("Funbox連線中...")

                r=requests.get(
                    site["url"],
                    headers={
                        "User-Agent":"Mozilla/5.0"
                    },
                    timeout=20
                )

print("Funbox完成")

                html=r.text


            else:

                html=selenium_html(
                    site["url"]
                )


            print(
                site["name"],
                "HTML:",
                len(html)
            )


            soup=BeautifulSoup(
                html,
                "html.parser"
            )


            count=0


            for a in soup.find_all("a"):


                text=a.get_text(
                    " ",
                    strip=True
                )


                href=a.get("href")


                if not href:
                    continue



                # MOMO只抓商品頁

                if site["name"]=="MOMO":

                    if "/goods/" not in href:

                        continue



                # 其他商品網址

                if site["name"]=="墊腳石":

                    if "Search" in href:
                       continue


                elif site["name"]=="誠品":

                    if "/product/" not in href:
                       continue


                elif site["name"]=="蝦皮商城":

                    if "-i." not in href:
                       continue


                else:

                    if not any(
                       x in href
                       for x in [
                       "/products/",
                       "/goods/",
                       "/item/",
                       "Product"
                        ]
                    ):
                        continue

                keytext=text.upper()


                # 關鍵字限制

                if not (
                    "BEYBLADE" in keytext
                    or "戰鬥陀螺" in text
                ):

                    continue



                # 去除垃圾

                if len(text)<8:

                    continue



                # 補完整網址
                if href.startswith("/"):
                    href = urljoin(
                        site["url"],
                        href
                    )


                key=(
                    site["name"]
                    +"|"
                    +href
                )


                stock=check_stock(
                    text
                )


                products[key]={

                    "site":site["name"],
                    "name":text,
                    "url":href,
                    "stock":stock

                }


                count+=1


                print(
                    "抓到:",
                    site["name"],
                    text[:80]
                )


            print(
                site["name"],
                "抓到商品:",
                count
            )


        except Exception as e:
            print(site["name"],"錯誤")
            traceback.print_exc()



    return products




# =================開始=================

seen=load_seen()


first_run = len(seen)==0


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

        time.sleep(60)



    for key,p in products.items():


        site=p["site"]
        name=p["name"]
        url=p["url"]
        stock=p["stock"]



        # 新商品

        if key not in seen:


            if not first_run:


                msg=f"""
🆕 新商品

來源:
{site}

商品:
{name}

🔗 點擊購買:
{url}
"""


                send_telegram(msg)

                print(msg)



            seen[key]={

                "site":site,
                "name":name,
                "url":url,
                "stock":stock

            }



        else:


            old=seen[key].get(
                "stock",
                False
            )


            # 缺貨->有貨

            if old==False and stock==True:


                msg=f"""
🔥 補貨通知

來源:
{site}

商品:
{name}

🔗 點擊購買:
{url}
"""


                send_telegram(msg)

                print(msg)



            seen[key]["stock"]=stock



    save_seen(seen)



    first_run=False


    time.sleep(
        CHECK_TIME
    )

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
    port=int(os.environ.get("PORT", 10000))
)