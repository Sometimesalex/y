#!/usr/bin/env python3

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
QC = ROOT / "querycorpora"
OUT_DIR = ROOT / "Interpreteroutput"
OUT_FILE = OUT_DIR / "interpreter_result.json"

files = sorted(QC.glob("*.json"))

if not files:
    print("no sensory files")
    exit()

latest = files[-1]

print(f"[interpreter] using {latest}")

# read the latest querycorpora file
data = json.loads(latest.read_text(encoding="utf-8"))

# ensure output directory exists
OUT_DIR.mkdir(parents=True, exist_ok=True)

# write mechanical pass-through output
with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"[interpreter] wrote {OUT_FILE}")
