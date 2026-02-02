#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RAW_PATH = ROOT / "corpora" / "sikhism" / "raw" / "guru_granth_sahib.json"
OUT_PATH = ROOT / "corpora" / "sikhism" / "verses_enriched.json"


def main():
    if not RAW_PATH.exists():
        raise SystemExit(f"Missing source file: {RAW_PATH}")

    with open(RAW_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    verses = []

    # hymn counter per ang (page)
    per_ang = {}

    for row in raw:
        ang = row.get("ang")
        text_en = (row.get("text_en") or "").strip()

        if not ang or not text_en:
            continue

        # increment verse index per ang
        per_ang.setdefault(ang, 0)
        per_ang[ang] += 1
        verse_idx = per_ang[ang]

        verses.append({
            "corpus": "sikhism",
            "work_title": "Guru Granth Sahib",
            "chapter": str(ang),          # Ang → chapter
            "verse": str(verse_idx),     # hymn index on that Ang
            "raga": row.get("raga", ""),
            "author": row.get("author", ""),
            "text": text_en,
            "text_pa": row.get("text_pa", "")
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    print("Verses written:", len(verses))


if __name__ == "__main__":
    main()
