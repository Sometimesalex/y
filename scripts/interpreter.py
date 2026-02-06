#!/usr/bin/env python3

import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QC = ROOT / "querycorpora"

files = sorted(QC.glob("*.json"))

if not files:
    print("no querycorpora files found")
    exit(0)

latest = files[-1]

with open(latest, encoding="utf-8") as f:
    data = json.load(f)

query = data.get("query", "")
results = data.get("results", [])

lines = []
lines.append("Interpreter online\n")
lines.append(f"Query: {query}\n")
lines.append(f"Results: {len(results)}\n")

for r in results[:5]:
    ref = f'{r.get("work_title","")} {r.get("chapter","")}:{r.get("verse","")}'.strip()
    lines.append(ref)
    lines.append(r.get("text",""))
    lines.append("")

print("\n".join(lines))
