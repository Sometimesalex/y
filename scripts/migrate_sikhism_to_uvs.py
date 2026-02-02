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

MAX_RETRIES = 5
TIMEOUT = 40
SLEEP = 1.0

def fetch_ang(n):
    url = BASE.format(n)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return r.text
        except Exception as e:
            print(f"Retry {attempt}/{MAX_RETRIES} for Ang {n}:", e)
            time.sleep(5 * attempt)

    raise RuntimeError(f"Failed Ang {n}")

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
    existing = []

    if OUT_FILE.exists():
        with open(OUT_FILE, encoding="utf-8") as f:
            existing = json.load(f)
        print("Resuming with", len(existing), "existing verses")

    done_angs = {v["chapter"] for v in existing}

    all_verses = existing[:]

    for ang in range(1, 1431):
        if ang in done_angs:
            continue

        print("Fetching Ang", ang)
        html = fetch_ang(ang)
        verses = parse_ang(html, ang)
        all_verses.extend(verses)

        # checkpoint every Ang
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_verses, f, ensure_ascii=False, indent=2)

        time.sleep(SLEEP)

    print("Done. Total verses:", len(all_verses))

if __name__ == "__main__":
    main()
