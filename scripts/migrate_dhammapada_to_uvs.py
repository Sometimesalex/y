cat > scripts/migrate_dhammapada_to_uvs.py <<'EOF'
#!/usr/bin/env python3

import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SRC = ROOT / "corpora" / "buddhism" / "raw" / "dhammapada.txt"
OUT = ROOT / "corpora" / "buddhism" / "verses_enriched.json"

VERSE_RE = re.compile(r"^\s*(\d+)\.\s+(.*)")
END_MARK = "*** END OF THE PROJECT GUTENBERG EBOOK"

def main():
    with open(SRC, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    verses = []
    current = None

    for line in lines:
        if END_MARK in line:
            break

        m = VERSE_RE.match(line)
        if m:
            if current:
                verses.append(current)

            vnum = int(m.group(1))
            text = m.group(2).strip()

            current = {
                "corpus": "buddhism_dhammapada_en",
                "tradition": "buddhism",
                "work": "dhammapada",
                "work_title": "Dhammapada",
                "chapter": 1,
                "verse": vnum,
                "section": "1",
                "subsection": str(vnum),
                "text": text,
                "sentiment": 0.0,
                "dominance": 0.0,
                "compassion": 0.0,
                "violence": 0.0,
                "agency": 0.0,
            }
        elif current and line.strip():
            current["text"] += " " + line.strip()

    if current:
        verses.append(current)

    verses.sort(key=lambda x: x["verse"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    print("Verses written:", len(verses))


if __name__ == "__main__":
    main()
EOF
