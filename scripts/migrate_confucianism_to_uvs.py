#!/usr/bin/env python3

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RAW_TXT = ROOT / "corpora" / "confucianism" / "raw" / "confucianism.txt"
OUT_JSON = ROOT / "corpora" / "confucianism" / "verses_enriched.json"

CORPUS_NAME = "confucianism"
WORK_TITLE = "Confucian Analects (James Legge)"

# Simple patterns
CHAP_RE = re.compile(r"^\s*CHAP\.|^\s*BOOK", re.IGNORECASE)
GUTENBERG_START = "*** START OF"
GUTENBERG_END = "*** END OF"


def main():
    if not RAW_TXT.exists():
        raise SystemExit(f"Missing source file: {RAW_TXT}")

    text = RAW_TXT.read_text(encoding="utf-8", errors="ignore").splitlines()

    # Strip Gutenberg header/footer
    started = False
    cleaned = []
    for line in text:
        if GUTENBERG_START in line:
            started = True
            continue
        if GUTENBERG_END in line:
            break
        if started:
            cleaned.append(line.rstrip())

    verses = []

    chapter = 0
    verse = 0

    for line in cleaned:
        l = line.strip()

        if not l:
            continue

        # Skip obvious Chinese-only lines / bracket markers
        if l.startswith("【") or l.startswith("論語"):
            continue

        # Chapter markers
        if CHAP_RE.search(l):
            chapter += 1
            verse = 0
            continue

        # Skip Gutenberg noise
        if l.lower().startswith("the project gutenberg"):
            continue

        # Heuristic: keep English prose lines
        if re.search(r"[a-zA-Z]", l):
            verse += 1
            verses.append({
                "corpus": CORPUS_NAME,
                "work_title": WORK_TITLE,
                "chapter": chapter if chapter > 0 else 1,
                "verse": verse,
                "text": l
            })

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)

    print("Written verses:", len(verses))


if __name__ == "__main__":
    main()
