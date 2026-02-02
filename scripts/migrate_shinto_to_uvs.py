#!/usr/bin/env python3

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

RAW = ROOT / "corpora" / "shinto" / "raw" / "kojiki.txt"
OUT = ROOT / "corpora" / "shinto" / "verses_enriched.json"


def main():
    if not RAW.exists():
        print("Missing:", RAW)
        return

    text = RAW.read_text(encoding="utf-8", errors="ignore")

    # Normalize spacing
    text = re.sub(r"\r", "", text)

    # Split by blank lines (paragraph blocks)
    blocks = re.split(r"\n\s*\n+", text)

    verses = []
    idx = 1

    for b in blocks:
        b = b.strip()
        if len(b) < 80:
            continue

        b = " ".join(l.strip() for l in b.splitlines())

        verses.append({
            "corpus": "shinto_kojiki_en",
            "work_title": "Kojiki",
            "chapter": "",
            "verse": str(idx),
            "ref": f"Kojiki:{idx}",
            "text": b
        })

        idx += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    print("Written verses:", len(verses))


if __name__ == "__main__":
    main()
