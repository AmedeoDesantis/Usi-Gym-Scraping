import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import csv
import os

URL = "https://sport.usi.ch/it/lugano"
CSV_FILE = "occupancy_log.csv"

html = requests.get(URL, timeout=10).text
soup = BeautifulSoup(html, "html.parser")

el = soup.select_one("p.occupancy-text")

if not el:
    raise RuntimeError("Elemento non trovato")

value = el.get_text(strip=True)
date, time = datetime.now(ZoneInfo("Europe/Zurich")).strftime("%Y-%m-%d,%H:%M").split(",")


file_exists = os.path.isfile(CSV_FILE)

with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow(["day", "hour", "value"])
    writer.writerow([date, time, value])

print(f"{date}, {time} → {value}")