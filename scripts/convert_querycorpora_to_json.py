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

# -------------------------------------------------
# 1. Load source safely (JSON OR raw text)
# -------------------------------------------------

raw_text = None
source_obj = None

try:
    with open(latest, "r", encoding="utf-8") as f:
        source_obj = json.load(f)

    # JSON loaded successfully
    raw_text = (
        source_obj.get("content")
        or source_obj.get("raw")
        or source_obj.get("text")
    )

except json.JSONDecodeError:
    # Not JSON — treat entire file as raw transcript
    raw_text = latest.read_text(encoding="utf-8")

if not raw_text or not raw_text.strip():
    raise RuntimeError("Source file contains no readable transcript")

# -------------------------------------------------
# 2. Parse transcript into corpora
# -------------------------------------------------

question = ""
corpora = defaultdict(list)

current_corpus = None
current_entry = None

for line in raw_text.splitlines():
    line = line.rstrip()

    if line.startswith("Asking:"):
        question = line.replace("Asking:", "").strip()
        continue

    m = re.match(r"^Corpus:\s+(.+)$", line)
    if m:
        current_corpus = m.group(1).strip()
        continue

    m = re.match(r"^\[(.+?)\]$", line)
    if m and current_corpus:
        current_entry = {
            "ref": m.group(1),
            "text": "",
            "score": 1.0
        }
        corpora[current_corpus].append(current_entry)
        continue

    if current_entry and line.strip():
        current_entry["text"] += line + " "

# -------------------------------------------------
# 3. Build strict converted JSON
# -------------------------------------------------

converted = {
    "source_file": latest.name,
    "encoding": "utf-8",
    "format": "parsed-transcript-v1",
    "question": question,
    "raw_transcript": raw_text,   # FULL, UNMODIFIED
    "corpora": corpora,
    "stats": {
        "corpus_count": len(corpora),
        "entry_count": sum(len(v) for v in corpora.values())
    }
}

out_file = QC_DIR / f"{latest.stem}.converted.json"

with open(out_file, "w", encoding="utf-8") as f:
    json.dump(converted, f, indent=2, ensure_ascii=False)

print(f"[converter] wrote structured JSON: {out_file}")
print(f"[converter] corpora={converted['stats']['corpus_count']} "
      f"entries={converted['stats']['entry_count']}")
