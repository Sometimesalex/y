#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SRC = ROOT / "corpora" / "tanakh" / "tanakh.json"
OUT = ROOT / "corpora" / "tanakh" / "verses_enriched.json"

def slug(s):
    return s.lower().replace(" ", "-").replace("_", "-")

def main():
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    verses = []

    # Expecting structure:
    # {
    #   "Genesis": { "1": { "1": "...", ... }, ... },
    #   ...
    # }
    # OR list of books with chapters/verses.
    #
    # We support both patterns.

    if isinstance(data, dict):
        books = data.items()
    else:
        raise RuntimeError("Unexpected tanakh.json structure (not dict at top level)")

    for book_title, chapters in books:
        work = slug(book_title)

        for ch_key, ch_val in chapters.items():
            chapter = int(ch_key)

            for v_key, verse_text in ch_val.items():
                verse = int(v_key)

                verses.append({
                    "corpus": "judaism_tanakh_en",
                    "tradition": "judaism",
                    "work": work,
                    "work_title": book_title,
                    "chapter": chapter,
                    "verse": verse,
                    "section": str(chapter),
                    "subsection": str(verse),
                    "text": verse_text.strip(),

                    # analysis fields (same as others)
                    "sentiment": 0.0,
                    "dominance": 0.0,
                    "compassion": 0.0,
                    "violence": 0.0,
                    "agency": 0.0,
                })

    verses.sort(key=lambda x: (x["work"], x["chapter"], x["verse"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    print("Verses written:", len(verses))

if __name__ == "__main__":
    main()
