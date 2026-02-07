#!/usr/bin/env python3

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

QC = ROOT / "querycorpora"
OUT_DIR = ROOT / "Interpreteroutput"
OUT_FILE = OUT_DIR / "interpreter_result.json"

# Only read converted JSON files
files = sorted(QC.glob("*.converted.json"))

if not files:
    print("[interpreter] no .converted.json files found")
    sys.exit(1)

latest = files[-1]
print(f"[interpreter] using {latest}")

# Load converted JSON
with open(latest, "r", encoding="utf-8") as f:
    data = json.load(f)

# Print the data so we can see it in workflow logs
print("[interpreter] converted JSON content:")
print(json.dumps(data, indent=2, ensure_ascii=False))

# Ensure output directory exists
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Mechanical pass-through (no interpretation yet)
with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"[interpreter] wrote {OUT_FILE}")
