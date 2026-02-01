#!/usr/bin/env python3

import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SRC = ROOT / "corpora" / "buddhism" / "raw" / "dhammapada.txt"
OUT = ROOT / "corpora" / "buddhism" / "verses_enriched.json"

# Matches:
# 153. text
# 153, 154. text
VERSE_RE = re.compile(r"^\s*(\d+)(?:,\s*(\d+))?\.\s+(.*)")

MAX_VERSE = 423

def main():
    with open(SRC, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    verses = []
    current_nums = []
    current_text = ""

    started = False

    for line in lines:
        m = VERSE_RE.match(line)

        if m:
            started = True

            # flush previous
            if current_nums:
                for v in current_nums:
                    verses.append(make_entry(v, current_text))

            v1 = int(m.group(1))
            v2 = m.group(2)

            if v2:
                current_nums = [v1, int(v2)]
            else:
                current_nums = [v1]

            current_text = m.group(3).strip()

        elif started and current_nums and line.strip():
            # continuation line
            current_text += " " + line.strip()

    # final flush
    if current_nums:
        for v in current_nums:
            verses.append(make_entry(v, current_text))

    # hard trim (true Dhammapada length)
    verses = [v for v in verses if v["verse"] <= MAX_VERSE]

    verses.sort(key=lambda x: x["verse"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    print("Verses written:", len(verses))


def make_entry(vnum, text):
    return {
        "corpus": "buddhism_dhammapada_en",
        "tradition": "buddhism",
        "work": "dhammapada",
        "work_title": "Dhammapada",
        "chapter": 1,
        "verse": vnum,
        "section": "1",
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
