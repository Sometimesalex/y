#!/usr/bin/env python3

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
QC_DIR = ROOT / "querycorpora"

# find all querycorpora files (original outputs)
files = sorted(QC_DIR.glob("*.json"))

if not files:
    print("[converter] no querycorpora files found")
    sys.exit(1)

latest = files[-1]
print(f"[converter] using source file: {latest.name}")

# read raw content EXACTLY as-is
raw_text = latest.read_text(encoding="utf-8")

# build a strict JSON wrapper (no modification)
converted = {
    "source_file": latest.name,
    "encoding": "utf-8",
    "format": "raw-transcript",
    "content": raw_text
}

# output filename (clearly marked as converted)
out_file = QC_DIR / f"{latest.stem}.converted.json"

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(converted, f, indent=2, ensure_ascii=False)

print(f"[converter] wrote converted JSON: {out_file}")
