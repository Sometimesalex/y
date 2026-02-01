#!/usr/bin/env python3

import sys
import json
import math
from collections import defaultdict, Counter
from pathlib import Path

from prolog_reader import LocalWordNet


ROOT = Path(__file__).resolve().parents[1]

KJV_PATH = ROOT / "corpora/kjv/verses_enriched.json"
QURAN_PATH = ROOT / "corpora/quran/verses_enriched.json"
GCIDE_PATH = ROOT / "corpora/GCIDE/gcide.json"


def tokenize(text):
    return [t.lower() for t in text.replace("?", " ").replace(".", " ").split()]


def load_uvs(path):
    with open(path) as f:
        return json.load(f)


def load_gcide():
    if not GCIDE_PATH.exists():
        return {}
    with open(GCIDE_PATH) as f:
        return json.load(f)


def cosine(a, b):
    dot = sum(a[k] * b.get(k, 0) for k in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def vec(tokens):
    return Counter(tokens)


def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question\"")
        return

    query = sys.argv[1]
    print("\nAsking:", query)

    print("Loading verses...")
    verses = []
    verses += load_uvs(KJV_PATH)
    verses += load_uvs(QURAN_PATH)
    print("Loaded", len(verses), "verses.")

    print("Loading GCIDE...")
    gcide = load_gcide()
    print("GCIDE entries:", len(gcide))

    print("Loading WordNet...")
    wn = LocalWordNet(ROOT / "prolog")
    wn.load_all()
    print("WordNet ready.\n")

    q_tokens = tokenize(query)
    q_vec = vec(q_tokens)

    # GCIDE fallback for single-term queries
    if len(q_tokens) == 1 and q_tokens[0] in gcide:
        print(f"\nGCIDE definition for '{q_tokens[0]}':\n")
        for d in gcide[q_tokens[0]][:5]:
            print(" •", d)
        print()

    scored = []

    for v in verses:
        t = tokenize(v["text"])
        s = cosine(q_vec, vec(t))
        if s > 0:
            scored.append((s, v))

    scored.sort(key=lambda x: -x[0])

    by_corpus = defaultdict(list)
    for score, verse in scored:
        verse = dict(verse)
        verse["score"] = score
        by_corpus[verse["corpus"]].append(verse)

    for corpus in sorted(by_corpus.keys()):
        print("\n==============================")
        print(corpus)
        print("==============================\n")

        top = by_corpus[corpus][:5]

        for i, v in enumerate(top, 1):
            print(f"{i}. [{v['work_title']} {v['chapter']}:{v['verse']}]")
            print(v["text"])
            print(f"(score {v['score']:.4f})\n")


if __name__ == "__main__":
    main()
