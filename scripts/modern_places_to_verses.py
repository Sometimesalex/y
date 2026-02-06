#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "corpora" / "modern_history" / "raw" / "ne_places.csv"
OUT = ROOT / "corpora" / "modern_history" / "verses_enriched.json"

with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

rows = []

for feat in data.get("features", []):
    props = feat.get("properties", {})
    geom = feat.get("geometry", {})

    name = props.get("NAME", "") or props.get("name", "")
    country = props.get("SOV0NAME", "") or props.get("adm0name", "")
    pop = props.get("POP_MAX", "") or props.get("pop_max", "")

    coords = geom.get("coordinates", [])
    if len(coords) >= 2:
        lon, lat = coords[0], coords[1]
    else:
        lat = lon = ""

    if not name:
        continue

    text = f"{name} {country} {lat} {lon} population {pop}"

    rows.append({
        "corpus": "modern_history",
        "work_title": "modern_history",
        "chapter": "place",
        "verse": name,
        "text": text
    })

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

print("Written:", OUT)
print("Rows:", len(rows))
