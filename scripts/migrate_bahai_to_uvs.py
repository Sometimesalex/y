#!/usr/bin/env python3

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RAW = ROOT / "corpora" / "bahai" / "raw" / "thehiddenwords.txt"
OUT = ROOT / "corpora" / "bahai" / "verses_enriched.json"

def main():
    if not RAW.exists():
        print("Missing:", RAW)
        return

    verses = []
    corpus = "bahai_hidden_words"

    with open(RAW, encoding="utf-8", errors="ignore") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    idx = 1
    for line in lines:
        # skip obvious headers
        if line.lower().startswith(("the hidden words", "bahá", "baha")):
            continue

        verses.append({
            "corpus": corpus,
            "work_title": "The Hidden Words",
            "chapter": "",
            "verse": str(idx),
            "text": line
        })
        idx += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    print("Written verses:", len(verses))


if __name__ == "__main__":
    main()
