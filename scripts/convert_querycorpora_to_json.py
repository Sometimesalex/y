#!/usr/bin/env python3

from pathlib import Path
import json
import sys
import re
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
QC_DIR = ROOT / "querycorpora"

files = sorted(QC_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)

if not files:
    print("[converter] no querycorpora files found")
    sys.exit(1)

latest = files[-1]
print(f"[converter] using source file: {latest.name}")

# --- load original JSON exactly ---
with open(latest, "r", encoding="utf-8") as f:
    original = json.load(f)

raw_text = original.get("content") or original.get("raw") or ""

if not raw_text:
    raise RuntimeError("Source JSON contains no transcript content")

# --- parsing ---
question = ""
corpora = defaultdict(list)

current_corpus = None
current_ref = None

lines = raw_text.splitlines()

for line in lines:
    line = line.rstrip()

    # Question line
    if line.startswith("Asking:"):
        question = line.replace("Asking:", "").strip()
        continue

    # Corpus header
    m = re.match(r"^Corpus:\s+(.+)$", line)
    if m:
        current_corpus = m.group(1).strip()
        continue

    # Reference header
    m = re.match(r"^\[(.+?)\]$", line)
    if m and current_corpus:
        current_ref = m.group(1)
        corpora[current_corpus].append({
            "ref": current_ref,
            "text": "",
            "score": 1.0
        })
        continue

    # Accumulate verse text
    if current_corpus and corpora[current_corpus]:
        if line.strip():
            corpora[current_corpus][-1]["text"] += line + " "

# --- final converted structure ---
converted = {
    "source_file": latest.name,
    "encoding": "utf-8",
    "format": "parsed-transcript-v1",
    "question": question,
    "raw_transcript": raw_text,      # FULL ORIGINAL, UNTOUCHED
    "corpora": corpora,               # STRUCTURED DATA
    "stats": {
        "corpus_count": len(corpora),
        "entry_count": sum(len(v) for v in corpora.values())
    }
}

out_file = QC_DIR / f"{latest.stem}.converted.json"

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(converted, f, indent=2, ensure_ascii=False)

print(f"[converter] wrote structured JSON: {out_file}")
print(f"[converter] corpora: {len(corpora)} | entries: {converted['stats']['entry_count']}")
