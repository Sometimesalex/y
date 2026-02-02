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

    # Split on SECT. markers
    parts = re.split(r"\n\s*SECT\.\s*", text)

    verses = []
    idx = 1

    for part in parts:
        part = part.strip()
        if not part:
            continue

        lines = [l.strip() for l in part.splitlines() if l.strip()]
        if not lines:
            continue

        body = " ".join(lines)

        verses.append({
            "corpus": "shinto_kojiki_en",
            "work_title": "Kojiki",
            "chapter": "",
            "verse": str(idx),
            "ref": f"Kojiki:{idx}",
            "text": body
        })

        idx += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    print("Written verses:", len(verses))


if __name__ == "__main__":
    main()
