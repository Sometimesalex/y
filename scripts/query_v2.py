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

GCIDE_PATH = ROOT / "corpora" / "GCIDE" / "gcide.json"

STOPWORDS = {
    "a","an","the","and","or","but","if","then","else",
    "is","are","was","were","be","been","being",
    "i","me","my","mine","you","your","yours","he","she","it","we","they",
    "this","that","these","those",
    "what","which","who","whom","whose","when","where","why","how",
    "should","would","could","can","may","might","must","shall",
    "do","does","did",
    "to","of","in","on","at","by","for","with","about","from","into","over","under",
}

def load_gcide():
    if not GCIDE_PATH.exists():
        return {}
    with open(GCIDE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    print("GCIDE entries:", len(data))
    return data

def tokenize(question):
    raw = [
        t.lower()
        for t in re.findall(r"[a-zA-Z']+", question)
    ]

    filtered = [
        t for t in raw
        if t not in STOPWORDS and len(t) > 1
    ]

    if not filtered:
        filtered = raw

    return filtered

def load_all_verses():
    allv = []
    for p in CORPORA:
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            allv.extend(json.load(f))
    return allv

def score(text, terms):
    t = text.lower()
    return sum(t.count(w) for w in terms)

def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"question\"")
        return

    question = sys.argv[1]
    print("\nAsking:", question)

    query_terms = tokenize(question)
    print("\nQuery terms:", query_terms)

    gcide = load_gcide()

    for term in query_terms:
        if term in gcide:
            print(f"\n---\nGCIDE definition for '{term}':\n")
            for d in gcide[term]:
                print(" •", d)

    print("\nLoading WordNet...")
    try:
        wn = LocalWordNet(ROOT / "prolog")
        print("WordNet ready.\n")
    except Exception as e:
        print("WordNet skipped (non-fatal):", e)

    verses = load_all_verses()
    print("Loaded", len(verses), "verses.")

    grouped = defaultdict(list)

    for v in verses:
        s = score(v.get("text",""), query_terms)
        if s:
            grouped[v["corpus"]].append((s, v))

    for corpus, items in grouped.items():
        print("\n==============================")
        print("Corpus:", corpus)
        print("==============================\n")

        items.sort(key=lambda x: -x[0])

        for _, v in items[:5]:
            ref = f'[{v["work_title"]}] {v["chapter"]}:{v["verse"]}'
            print(ref)
            print(v["text"])
            if "text_he" in v:
                print(v["text_he"])
            print()

if __name__ == "__main__":
    main()
