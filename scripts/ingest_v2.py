#!/usr/bin/env python3

import json
import sys
import re
from pathlib import Path
from collections import defaultdict

from prolog_reader import LocalWordNet


ROOT = Path(__file__).resolve().parents[1]

CORPORA = [
    ROOT / "corpora" / "kjv" / "verses_enriched.json",
    ROOT / "corpora" / "quran" / "verses_enriched.json",
    ROOT / "corpora" / "tanakh" / "verses_enriched.json",
    ROOT / "corpora" / "buddhism" / "verses_enriched.json",
]

TOP_N = 5


STOPWORDS = {
    "the","a","an","and","or","of","to","in","on","at","for","with",
    "is","are","was","were","be","been","being",
    "i","you","he","she","it","we","they","me","him","her","them",
    "my","your","his","their","our",
    "what","when","where","why","how",
    "this","that","these","those",
    "do","does","did",
    "will","shall","would","could"
}


def tokenize(s):
    return re.findall(r"[a-zA-Z']+", s.lower())


def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question\"")
        sys.exit(1)

    query = sys.argv[1]
    print("\nAsking:", query)

    raw = tokenize(query)
    query_terms = [t for t in raw if t not in STOPWORDS]

    print("\nQuery terms:", query_terms)

    # ---- WordNet ----
    wn = None
    try:
        wn = LocalWordNet()
        wn.load_minimal()
        print("WordNet ready.")
    except Exception as e:
        print("WordNet skipped (non-fatal):", e)

    expanded = set()
    boost = set()

    for t in query_terms:
        # hard boost Jesus
        if t == "jesus":
            boost.add(t)
            expanded.add(t)
            continue

        expanded.add(t)

        if wn:
            try:
                expanded |= set(wn.get_lemmas(t))
                expanded |= set(wn.get_hypernyms(t))
            except:
                pass

    print("\nExpanded terms:", sorted(expanded))

    # ---- Load verses ----
    verses = []

    for path in CORPORA:
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            verses += json.load(f)

    print("Loaded", len(verses), "verses.")

    by_corpus = defaultdict(list)

    for v in verses:
        text = v.get("text","").lower()

        # must contain boosted term if present
        if boost:
            if not any(b in text for b in boost):
                continue

        for t in expanded:
            if t in text:
                by_corpus[v["corpus"]].append(v)
                break

    # ---- Output ----
    for corpus, hits in by_corpus.items():
        print("\n==============================")
        print("Corpus:", corpus)
        print("==============================\n")

        for v in hits[:TOP_N]:
            ref = f'[{v.get("work_title","")}] {v.get("chapter")}:{v.get("verse")}'
            print(ref)
            print(v["text"].strip())
            print()

if __name__ == "__main__":
    main()
