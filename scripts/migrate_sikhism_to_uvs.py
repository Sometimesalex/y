#!/usr/bin/env python3

import json
import time
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "corpora" / "sikhism"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_FILE = OUT_DIR / "verses_enriched.json"
FAIL_FILE = OUT_DIR / "failed_angs.txt"

BASE = "https://api.sikhitothemax.org/ang/{}"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

MAX_RETRIES = 6
TIMEOUT = 40
SLEEP = 0.8

def fetch_ang(n):
    url = BASE.format(n)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"Retry {attempt}/{MAX_RETRIES} Ang {n}")
            time.sleep(5 * attempt)

    return None

def main():
    existing = []
    failed = set()

    if OUT_FILE.exists():
        existing = json.loads(OUT_FILE.read_text())

    if FAIL_FILE.exists():
        failed = set(int(x) for x in FAIL_FILE.read_text().splitlines() if x.strip())

    done = {v["chapter"] for v in existing}

    all_verses = existing[:]

    for ang in range(1, 1431):
        if ang in done or ang in failed:
            continue

        print("Fetching Ang", ang)

        data = fetch_ang(ang)

        if data is None:
            failed.add(ang)
            FAIL_FILE.write_text("\n".join(str(x) for x in sorted(failed)))
            continue

        idx = 1

        for line in data.get("lines", []):
            gu = line.get("gurmukhi", "").strip()
            en = line.get("translation", {}).get("english", "").strip()

            if not gu and not en:
                continue

            bad = ("copyright", "electronic", "united states")
            joined = (gu + " " + en).lower()
            if any(b in joined for b in bad):
                continue

            all_verses.append({
                "corpus": "sikhism",
                "work_title": "Guru Granth Sahib",
                "chapter": ang,
                "verse": idx,
                "text": en,
                "text_gu": gu
            })

            idx += 1

        OUT_FILE.write_text(json.dumps(all_verses, ensure_ascii=False, indent=2))
        time.sleep(SLEEP)

    print("Done.")
    print("Verses:", len(all_verses))
    print("Failed Angs:", sorted(failed))

if __name__ == "__main__":
    main()
