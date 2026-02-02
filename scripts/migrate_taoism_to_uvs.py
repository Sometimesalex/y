#!/usr/bin/env python3

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpora" / "taoism" / "raw" / "taoism.txt"
OUT = ROOT / "corpora" / "taoism" / "verses_enriched.json"

CHAPTER_RE = re.compile(r"^\s*Chapter\s+(\d+)", re.IGNORECASE)

# junk we explicitly ignore
JUNK = (
    "classics.mit.edu",
    "internet classics archive",
    "http://",
    "https://",
    "provided by",
    "translated by",
    "2/2/",
    "am",
)

def clean(line):
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    return line

def is_junk(line):
    l = line.lower()
    if not line:
        return True
    for j in JUNK:
        if j in l:
            return True
    return False

def main():
    text = RAW.read_text(encoding="utf-8", errors="ignore").splitlines()

    verses = []

    chapter = 0
    verse = 1
    buf = []

    for raw in text:
        line = clean(raw)

        if is_junk(line):
            continue

        m = CHAPTER_RE.match(line)
        if m:
            # flush previous buffer
            if buf:
                verses.append({
                    "corpus": "taoism",
                    "work_title": "Tao Te Ching",
                    "chapter": chapter,
                    "verse": verse,
                    "text": " ".join(buf).strip()
                })
                buf = []
                verse = 1

            chapter = int(m.group(1))
            continue

        # ignore PART headers
        if line.lower().startswith("part "):
            continue

        # ignore title lines
        if line.lower().startswith("the tao-te ching"):
            continue
        if line.lower().startswith("by lao"):
            continue

        # numbered poetic lines ("1. ...")
        if re.match(r"^\d+\.\s+", line):
            line = re.sub(r"^\d+\.\s+", "", line)

        buf.append(line)

        # flush on paragraph-sized blocks
        if line.endswith(".") and len(buf) >= 2:
            verses.append({
                "corpus": "taoism",
                "work_title": "Tao Te Ching",
                "chapter": chapter,
                "verse": verse,
                "text": " ".join(buf).strip()
            })
            verse += 1
            buf = []

    # final flush
    if buf and chapter > 0:
        verses.append({
            "corpus": "taoism",
            "work_title": "Tao Te Ching",
            "chapter": chapter,
            "verse": verse,
            "text": " ".join(buf).strip()
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(verses, ensure_ascii=False, indent=2))

    print("Written verses:", len(verses))

if __name__ == "__main__":
    main()
