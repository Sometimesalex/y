cat > scripts/migrate_tanakh_to_uvs.py <<'EOF'
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

    for book, chapters in data.items():
        work = slug(book)
        work_title = book

        for ch_key in sorted(chapters.keys(), key=lambda x: int(x)):
            chapter = chapters[ch_key]

            verse_num = 1

            # alternating Hebrew / English entries
            for i in range(0, len(chapter)-1, 2):
                he = chapter[i].get("verse_he","").strip()
                en = chapter[i+1].get("verse_en","").strip()

                if not en and not he:
                    continue

                verses.append({
                    "corpus": "judaism_tanakh_en",
                    "tradition": "judaism",
                    "work": work,
                    "work_title": work_title,
                    "chapter": int(ch_key),
                    "verse": verse_num,
                    "section": str(ch_key),
                    "subsection": str(verse_num),
                    "text": en,
                    "text_he": he,
                    "sentiment": 0.0,
                    "dominance": 0.0,
                    "compassion": 0.0,
                    "violence": 0.0,
                    "agency": 0.0
                })

                verse_num += 1

    verses.sort(key=lambda v: (v["work"], v["chapter"], v["verse"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    print("Verses written:", len(verses))

if __name__ == "__main__":
    main()
EOF
