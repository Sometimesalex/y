#!/usr/bin/env python3

import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SRC = ROOT / "corpora" / "hinduism" / "raw" / "bhagavad_gita.txt"
OUT = ROOT / "corpora" / "hinduism" / "verses_enriched.json"

CHAPTER_RE = re.compile(r"^\s*CHAPTER\s+([IVX]+)", re.IGNORECASE)
END_CHAPTER_RE = re.compile(r"HERE END", re.IGNORECASE)

ROMAN = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
    "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11,
    "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
    "XVI": 16, "XVII": 17, "XVIII": 18,
}

def main():
    with open(SRC, encoding="utf-8", errors="ignore") as f:
        raw = f.readlines()

    verses = []
    current_chapter = None
    buffer = []
    verse_idx = 0
    started = False

    for line in raw:
        m = CHAPTER_RE.match(line)

        if m:
            started = True

            if buffer and current_chapter:
                for chunk in buffer:
                    verse_idx += 1
                    verses.append(make_verse(current_chapter, verse_idx, chunk))
                buffer = []

            roman = m.group(1).upper()
            current_chapter = ROMAN.get(roman)
            verse_idx = 0
            continue

        if not started:
            continue

        if END_CHAPTER_RE.search(line):
            continue

        t = line.strip()
        if not t:
            if buffer:
                buffer.append("")
            continue

        buffer.append(t)

    if buffer and current_chapter:
        for chunk in buffer:
            verse_idx += 1
            verses.append(make_verse(current_chapter, verse_idx, chunk))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    chapters = sorted(set(v["chapter"] for v in verses))

    print("Verses written:", len(verses))
    print("Chapters:", chapters)

def make_verse(ch, vnum, text):
    return {
        "corpus": "hinduism_bhagavad_gita_en",
        "tradition": "hinduism",
        "work": "bhagavad_gita",
        "work_title": "Bhagavad Gita",
        "chapter": ch,
        "verse": vnum,
        "section": str(ch),
        "subsection": str(vnum),
        "text": text.strip(),
        "sentiment": 0.0,
        "dominance": 0.0,
        "compassion": 0.0,
        "violence": 0.0,
        "agency": 0.0,
    }

if __name__ == "__main__":
    main()
