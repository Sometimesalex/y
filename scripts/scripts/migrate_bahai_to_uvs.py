#!/usr/bin/env python3

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

RAW = ROOT / "corpora" / "bahai" / "raw" / "hidden_words.txt"
OUT = ROOT / "corpora" / "bahai" / "verses_enriched.json"

def clean_gutenberg(text: str) -> str:
    # remove Gutenberg headers/footers if present
    start = re.search(r"\*\*\* START OF", text)
    end = re.search(r"\*\*\* END OF", text)
    if start and end:
        text = text[start.end():end.start()]
    return text.strip()

def main():
    raw = RAW.read_text(encoding="utf-8", errors="ignore")
    raw = clean_gutenberg(raw)

    lines = [l.strip() for l in raw.splitlines() if l.strip()]

    verses = []
    buf = []
    idx = 1

    for line in lines:
        # new verse markers commonly used in Hidden Words
        if re.match(r"^(O |O SON|O CHILD|O YE|O FRIEND)", line, re.IGNORECASE):
            if buf:
                verses.append({
                    "ref": f"Hidden Words {idx}",
                    "text": " ".join(buf)
                })
                idx += 1
                buf = []
        buf.append(line)

    if buf:
        verses.append({
            "ref": f"Hidden Words {idx}",
            "text": " ".join(buf)
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(verses, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Written verses: {len(verses)}")

if __name__ == "__main__":
    main()
