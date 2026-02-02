#!/usr/bin/env python3

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpora" / "sikhism" / "raw" / "sikhism.txt"
OUT = ROOT / "corpora" / "sikhism" / "verses_enriched.json"

# Unicode block for Gurmukhi
GURMUKHI_RE = re.compile(r"[\u0A00-\u0A7F]")
PAGE_RE = re.compile(r"^\s*\d+\s*$")

def is_gurmukhi(s):
    return bool(GURMUKHI_RE.search(s))

def clean(line):
    line = line.replace("❀", "").strip()
    line = re.sub(r"\s+", " ", line)
    return line

def main():
    lines = RAW.read_text(encoding="utf-8", errors="ignore").splitlines()

    verses = []

    ang = 1
    verse = 1

    buf_en = []
    buf_gu = []

    for raw in lines:
        line = clean(raw)
        if not line:
            continue

        # page number
        if PAGE_RE.match(line):
            ang = int(line)
            verse = 1
            continue

        # skip obvious headings
        if line.isupper() and len(line) > 10:
            continue

        if is_gurmukhi(line):
            buf_gu.append(line)
        else:
            buf_en.append(line)

        # when we have both, flush
        if buf_en and buf_gu:
            en = " ".join(buf_en).strip()
            gu = " ".join(buf_gu).strip()

            # filter licence garbage just in case
            bad = ("electronic", "united states", "do not copy", "redistribute")
            joined = (en + gu).lower()
            if not any(b in joined for b in bad):
                verses.append({
                    "corpus": "sikhism",
                    "work_title": "Guru Granth Sahib",
                    "chapter": ang,
                    "verse": verse,
                    "text": en,
                    "text_gu": gu
                })
                verse += 1

            buf_en = []
            buf_gu = []

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(verses, ensure_ascii=False, indent=2))

    print("Written verses:", len(verses))

if __name__ == "__main__":
    main()
