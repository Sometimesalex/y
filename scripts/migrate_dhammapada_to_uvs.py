#!/usr/bin/env python3

import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SRC = ROOT / "corpora" / "buddhism" / "raw" / "dhammapada.txt"
OUT = ROOT / "corpora" / "buddhism" / "verses_enriched.json"

END_MARK = "*** END OF THE PROJECT GUTENBERG EBOOK"

# Matches:
# 153. text
# 153, 154. text
VERSE_RE = re.compile(r"^\s*(\d+)(?:,\s*(\d+))?\.\s+(.*)")

def emit(nums, text, verses):
    for n in nums:
        verses.append({
            "corpus": "buddhism_dhammapada_en",
            "tradition": "buddhism",
            "work": "dhammapada",
            "work_title": "Dhammapada",
            "chapter": 1,
            "verse": n,
            "section": "1",
            "subsection": str(n),
            "text": text.strip(),
            "sentiment": 0.0,
            "dominance": 0.0,
            "compassion": 0.0,
            "violence": 0.0,
            "agency": 0.0,
        })

def main():
    lines = SRC.read_text(encoding="utf-8", errors="ignore").splitlines()

    verses = []
    current_nums = None
    current_text = ""

    for line in lines:
        if END_MARK in line:
            break

        m = VERSE_RE.match(line)
        if m:
            if current_nums:
                emit(current_nums, current_text, verses)

            a = int(m.group(1))
            b = m.group(2)
            nums = [a]
            if b:
                nums.append(int(b))

            current_nums = nums
            current_text = m.group(3).strip()
        else:
            if current_nums and line.strip():
                current_text += " " + line.strip()

    if current_nums:
        emit(current_nums, current_text, verses)

    verses.sort(key=lambda x: x["verse"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(verses, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Verses written:", len(verses))


if __name__ == "__main__":
    main()
