#!/usr/bin/env python3

import json
import sys
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]

# Correct repo corpus paths
CORPORA = [
    ROOT / "corpora" / "kjv" / "verses_enriched.json",
    ROOT / "corpora" / "quran" / "verses_enriched.json",
    ROOT / "corpora" / "tanakh" / "verses_enriched.json",
    ROOT / "corpora" / "buddhism" / "verses_enriched.json",
    ROOT / "corpora" / "hinduism" / "verses_enriched.json",
    ROOT / "corpora" / "sikhism" / "verses_enriched.json",
    ROOT / "corpora" / "taoism" / "verses_enriched.json",
    ROOT / "corpora" / "confucianism" / "verses_enriched.json",
    ROOT / "corpora" / "shinto" / "verses_enriched.json",
]

WORD_RE = re.compile(r"[a-zA-Z']+")
TOP_N = 5


def tokenize(text):
    return WORD_RE.findall(text.lower())


def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question\"")
        sys.exit(1)

    query = sys.argv[1].lower()
    terms = tokenize(query)

    stop = {
        "the","a","an","and","or","to","of","i","you","he","she","it","we","they",
        "what","how","when","where","why","is","are","was","were","be","been","am"
    }

    terms = [t for t in terms if t not in stop]

    print("\nAsking:", query)
    print("Query terms:", terms)

    if not terms:
        print("No usable query terms.")
        sys.exit(0)

    all_verses = []

    for path in CORPORA:
        if not path.exists():
            print("Missing corpus:", path)
            continue

        with open(path, encoding="utf-8") as f:
            all_verses.extend(json.load(f))

    print("\nLoaded", len(all_verses), "verses total.")

    if not all_verses:
        print("No verses loaded. Abort.")
        return

    by_corpus = defaultdict(list)
    for v in all_verses:
        by_corpus[v.get("corpus","unknown")].append(v)

    for corpus, verses in sorted(by_corpus.items()):
        scored = []

        for v in verses:
            txt = v.get("text","").lower()
            score = sum(txt.count(t) for t in terms)

            if score > 0:
                scored.append((score, v))

        scored.sort(key=lambda x: x[0], reverse=True)

        print("\n==============================")
        print("Corpus:", corpus)
        print("==============================\n")

        if not scored:
            print("(no matches)")
            continue

        for _, v in scored[:TOP_N]:
            book = v.get("work_title","")
            ch = v.get("chapter","")
            ve = v.get("verse","")
            ref = f"{book} {ch}:{ve}".strip()

            print(f"[{ref}]")
            print(v.get("text","").strip())
            print()


if __name__ == "__main__":
    main()
