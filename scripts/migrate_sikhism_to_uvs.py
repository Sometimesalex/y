#!/usr/bin/env python3

import json
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "corpora" / "sikhism"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_FILE = OUT_DIR / "verses_enriched.json"

BASE = "https://www.sikhitothemax.org/ang?ang={}"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def fetch_ang(n):
    url = BASE.format(n)
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text

def parse_ang(html, ang):
    soup = BeautifulSoup(html, "html.parser")

    rows = soup.select("div.shabad-line")

    verses = []
    idx = 1

    for r in rows:
        gu = r.select_one(".gurbani")
        en = r.select_one(".translation")

        gu_txt = gu.get_text(" ", strip=True) if gu else ""
        en_txt = en.get_text(" ", strip=True) if en else ""

        if not gu_txt and not en_txt:
            continue

        # Skip license/footer junk if it ever appears
        bad = ("copyright", "do not copy", "electronic work", "united states")
        joined = (gu_txt + " " + en_txt).lower()
        if any(b in joined for b in bad):
            continue

        verses.append({
            "corpus": "sikhism",
            "work_title": "Guru Granth Sahib",
            "chapter": ang,
            "verse": idx,
            "text": en_txt,
            "text_gu": gu_txt
        })

        idx += 1

    return verses

def main():
    all_verses = []

    for ang in range(1, 1431):
        print("Fetching Ang", ang)
        html = fetch_ang(ang)
        verses = parse_ang(html, ang)
        all_verses.extend(verses)
        time.sleep(0.5)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_verses, f, ensure_ascii=False, indent=2)

    print("Written:", len(all_verses), "verses to", OUT_FILE)

if __name__ == "__main__":
    main()
