cat > scripts/migrate_gita_to_uvs.py <<'EOF'
#!/usr/bin/env python3

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SRC = ROOT / "corpora" / "hinduism" / "raw" / "bhagavad_gita.txt"
OUT = ROOT / "corpora" / "hinduism" / "verses_enriched.json"

CHAPTER_RE = re.compile(r"^CHAPTER\s+([IVXLCDM]+)", re.IGNORECASE)

ROMAN = {
    "I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,"VII":7,"VIII":8,"IX":9,
    "X":10,"XI":11,"XII":12,"XIII":13,"XIV":14,"XV":15,"XVI":16,
    "XVII":17,"XVIII":18
}

START_MARK = "CHAPTER I"
END_MARK = "*** END OF THE PROJECT GUTENBERG EBOOK"


def make_verse(chapter, verse, lines):
    return {
        "corpus": "hinduism_bhagavad_gita_en",
        "tradition": "hinduism",
        "work": "bhagavad_gita",
        "work_title": "Bhagavad Gita",
        "chapter": chapter,
        "verse": verse,
        "section": str(chapter),
        "subsection": f"{chapter}:{verse}",
        "text": " ".join(lines),
        "sentiment": 0.0,
        "dominance": 0.0,
        "compassion": 0.0,
        "violence": 0.0,
        "agency": 0.0,
    }


def main():
    lines = SRC.read_text(encoding="utf-8", errors="ignore").splitlines()

    verses = []
    chapter = None
    verse_num = 0
    buffer = []
    started = False

    for line in lines:
        if not started:
            if START_MARK in line:
                started = True
            continue

        if END_MARK in line:
            break

        m = CHAPTER_RE.match(line.strip())
        if m:
            if buffer and chapter:
                verses.append(make_verse(chapter, verse_num, buffer))
                buffer = []

            roman = m.group(1).upper()
            chapter = ROMAN.get(roman)
            verse_num = 0
            continue

        if chapter is None:
            continue

        if line.strip() == "":
            if buffer:
                verse_num += 1
                verses.append(make_verse(chapter, verse_num, buffer))
                buffer = []
            continue

        buffer.append(line.strip())

    if buffer and chapter:
        verse_num += 1
        verses.append(make_verse(chapter, verse_num, buffer))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(verses, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Verses written:", len(verses))
    print("Chapters:", sorted(set(v["chapter"] for v in verses)))


if __name__ == "__main__":
    main()
EOF
