#!/usr/bin/env python3

import json
import sys
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]

# All corpora (must match your folders)
CORPORA = [
    ROOT / "corpora" / "christianity_kjv" / "verses_enriched.json",
    ROOT / "corpora" / "islam_quran_en" / "verses_enriched.json",
    ROOT / "corpora" / "judaism_tanakh_en" / "verses_enriched.json",
    ROOT / "corpora" / "buddhism_dhammapada_en" / "verses_enriched.json",
    ROOT / "corpora" / "hinduism_bhagavad_gita_en" / "verses_enriched.json",
    ROOT / "corpora" / "sikhism" / "verses_enriched.json",
    ROOT / "corpora" / "taoism" / "verses_enriched.json",
    ROOT / "corpora" / "confucianism" / "verses_enriched.json",
    ROOT / "corpora" / "shinto_kojiki_en" / "verses_enriched.json",
]

GCIDE_PATH = ROOT / "corpora" / "GCIDE" / "gcide.json"

WORD_RE = re.compile(r"[a-zA-Z']+")

TOP_N = 5


def tokenize(text):
    return WORD_RE.findall(text.lower())


def load_gcide():
    if not GCIDE_PATH.exists():
        return {}
    with open(GCIDE_PATH, encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question\"")
        sys.exit(1)

    query = sys.argv[1].lower()
    query_terms = tokenize(query)

    # light stopwords only (do NOT kill meaning)
    stop = {"the", "a", "an", "and", "or", "to", "of"}
    query_terms = [t for t in query_terms if t not in stop]

    print("\nAsking:", query)
    print("Query terms:", query_terms)

    # GCIDE (context only)
    gcide = load_gcide()
    for t in query_terms:
        if t in gcide:
            print(f"\n---\nGCIDE definition for '{t}':\n")
            for d in gcide[t][:6]:
                print(" •", d)

    # Load verses
    all_verses = []
    for path in CORPORA:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                all_verses.extend(json.load(f))
        else:
            print("Missing corpus:", path)

    print("\nLoaded", len(all_verses), "verses total.")

    # Group by corpus
    by_corpus = defaultdict(list)
    for v in all_verses:
        by_corpus[v.get("corpus", "unknown")].append(v)

    # Score + show top N per corpus (ALWAYS)
    for corpus, verses in sorted(by_corpus.items()):
        scored = []

        for v in verses:
            text = v.get("text", "").lower()
            score = 0
            for t in query_terms:
                score += text.count(t)

            # IMPORTANT: never filter — always append
            scored.append((score, v))

        scored.sort(key=lambda x: x[0], reverse=True)

        print("\n==============================")
        print("Corpus:", corpus)
        print("==============================\n")

        for score, v in scored[:TOP_N]:
            work = v.get("work_title", corpus)
            ch = v.get("chapter", "")
            ve = v.get("verse", "")
            txt = v.get("text", "").strip()

            ref = f"{work} {ch}:{ve}".strip()
            print(f"[{ref}]")
            print(txt)
            print()

if __name__ == "__main__":
    main()
