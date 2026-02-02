#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RAW = ROOT / "corpora" / "jainism" / "raw" / "jainism.txt"
OUT = ROOT / "corpora" / "jainism" / "verses_enriched.json"

def main():
    if not RAW.exists():
        print("Missing jainism.txt")
        return

    verses = []

    with open(RAW, encoding="utf-8", errors="ignore") as f:
        lines = [l.strip() for l in f if l.strip()]

    idx = 1
    for line in lines:
        # skip very short junk
        if len(line) < 25:
            continue

        verses.append({
            "corpus": "jainism",
            "ref": str(idx),
            "text": line
        })
        idx += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    print("Written verses:", len(verses))

if __name__ == "__main__":
    main()
