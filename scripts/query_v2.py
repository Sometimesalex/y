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

STOPWORDS = {
    "the","a","an","and","or","of","to","in","on","for","with","is","are","was",
    "were","be","been","being","that","this","these","those","i","you","he","she",
    "it","we","they","how","when","what","why","who","whom","which","will","shall",
    "would","should","could","do","does","did"
}

TOP_N = 5

def tokenize(s):
    words = re.findall(r"[a-zA-Z']+", s.lower())
    return [w for w in words if w not in STOPWORDS]

def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question\"")
        return

    question = sys.argv[1]
    print("\nAsking:", question)

    query_terms = tokenize(question)
    print("\nQuery terms:", query_terms)

    # Load WordNet (best effort)
    wn = None
    try:
        wn = LocalWordNet()
    except Exception as e:
        print("WordNet skipped:", e)

    expanded = set(query_terms)
    boost = set()

    qt = set(query_terms)

    # Jesus arrival soft-expansion (BOOST ONLY)
    if "jesus" in qt and ("arrive" in qt or "return" in qt or "come" in qt):
        boost |= {"jesus","return","descend","appear","second"}

    # Normal WordNet expansion (soft)
    if wn:
        for t in query_terms:
            try:
                expanded |= set(wn.get_lemmas(t))
                expanded |= set(wn.get_hypernyms(t))
            except:
                pass

    expanded |= boost

    print("\nExpanded terms:", sorted(expanded))

    verses = []

    for path in CORPORA:
        if not path.exists():
            continue
        with open(path) as f:
            verses += json.load(f)

    print("Loaded", len(verses), "verses.")

    scored = defaultdict(list)

    for v in verses:
        text = v["text"].lower()

        score = 0.0

        for t in expanded:
            if t in text:
                score += 1.0
                if t in boost:
                    score += 2.0

        if score > 0:
            scored[v["corpus"]].append((score, v))

    for corpus, items in scored.items():
        items.sort(key=lambda x: -x[0])

        print("\n==============================")
        print("Corpus:", corpus)
        print("==============================\n")

        for score, v in items[:TOP_N]:
            ref = f"[{v.get('work_title','')}] {v.get('chapter','')}:{v.get('verse','')}"
            print(ref)
            print(v["text"])
            print()

if __name__ == "__main__":
    main()
