#!/usr/bin/env python3

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QC = ROOT / "querycorpora"

files = sorted(QC.glob("*.json"))

if not files:
    print("no sensory files")
    exit()

latest = files[-1]

print(latest.read_text(encoding="utf-8"))
