import requests
from bs4 import BeautifulSoup
import time
import os
import threading
from flask import Flask
from datetime import datetime

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URL = "https://upbit.com/service_center/notice"

last_id = 0  # will be set to latest on startup

def send_telegram(title, link):
    try:
        msg = f"""🚨 <b>NEW UPBIT LISTING!</b>

{title}

🔗 <a href="{link}">Open Announcement</a>
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"""
        
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except:
        pass

def get_current_max_id():
    try:
        r = requests.get(URL, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table tbody tr") or soup.select("tr")
        max_id = 0
        for row in rows[:10]:
            tds = row.find_all("td")
            if len(tds) < 2: continue
            a_tag = tds[0].find("a")
            if not a_tag: continue
            href = a_tag.get("href", "")
            if "?id=" not in href: continue
            try:
                cid = int(href.split("id=")[-1].split("&")[0])
                if cid > max_id:
                    max_id = cid
            except:
                continue
        return max_id
    except:
        return 0

def monitor_upbit():
    global last_id
    print("🚀 Upbit Listing Monitor STARTED (checks every 12 seconds)")
    
    # Set baseline on startup so we don't alert old listings
    last_id = get_current_max_id()
    print(f"Baseline set to latest ID: {last_id}")
    
    while True:
        try:
            r = requests.get(URL, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            rows = soup.select("table tbody tr") or soup.select("tr")
            
            for row in rows[:6]:  # only newest rows
                tds = row.find_all("td")
                if len(tds) < 2: continue
                a_tag = tds[0].find("a")
                if not a_tag: continue
                
                title = a_tag.get_text().strip()
                href = a_tag.get("href", "")
                if "?id=" not in href: continue
                
                try:
                    current_id = int(href.split("id=")[-1].split("&")[0])
                except:
                    continue
                
                full_link = "https://upbit.com" + href if href.startswith("/") else href
                
                if current_id > last_id and "신규거래지원안내" in title:
                    send_telegram(title, full_link)
                    print(f"✅ ALERT SENT → {title}")
                
                if current_id > last_id:
                    last_id = current_id
                    
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(12)

# Start monitor in background
threading.Thread(target=monitor_upbit, daemon=True).start()

@app.route('/')
def home():
    return "Upbit Listing Monitor is RUNNING ✅ (only alerts on new listings)"

@app.route('/health')
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
