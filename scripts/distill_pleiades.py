#!/usr/bin/env python3

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "corpora" / "human_flow" / "raw" / "databases" / "pleiades-places.csv"
OUT = ROOT / "corpora" / "human_flow" / "raw" / "human_flow_places.txt"

rows = []

with open(SRC, newline="", encoding="utf-8", errors="ignore") as f:
    reader = csv.DictReader(f)
    for r in reader:
        pid = r.get("id","").strip()
        title = r.get("title","").strip()
        lat = r.get("reprLat","").strip()
        lon = r.get("reprLong","").strip()
        start = r.get("minDate","").strip()
        end = r.get("maxDate","").strip()

        if not pid or not lat or not lon:
            continue

        rows.append(f"{pid}\t{title}\t{lat}\t{lon}\t{start}\t{end}")

with open(OUT, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(r + "\n")

print("Written:", OUT)
print("Rows:", len(rows))
