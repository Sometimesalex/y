#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "corpora" / "human_flow" / "human_flow.txt"
OUT = ROOT / "corpora" / "human_flow" / "verses_enriched.json"

rows = []

with open(SRC, encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue

        year = parts[0]
        kind = parts[1]
        text = " ".join(parts[2:])

        rows.append({
            "corpus": "human_flow",
            "work_title": "human_flow",
            "chapter": kind,
            "verse": year,
            "text": text
        })

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

print("Written:", OUT)
print("Rows:", len(rows))
