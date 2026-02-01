#!/usr/bin/env python3

import json
import sys
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]

CORPORA = [
    ROOT / "corpora" / "kjv" / "verses_enriched.json",
    ROOT / "corpora" / "quran" / "verses_enriched.json",
    ROOT / "corpora" / "tanakh" / "verses_enriched.json",
    ROOT / "corpora" / "buddhism" / "verses_enriched.json",
    ROOT / "corpora" / "hinduism" / "verses_enriched.json",
]

GCIDE_PATH = ROOT / "corpora" / "GCIDE" / "gcide.json"

WORD_RE = re.compile(r"[a-zA-Z']+")


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

    # minimal stoplist (keep expressions working)
    stop = {"the", "a", "an", "and", "or", "to", "of", "you", "how", "should"}
    query_terms = [t for t in query_terms if t not in stop]

    if not query_terms:
        print("No usable query terms.")
        sys.exit(0)

    print("\nAsking:", query)
    print("\nQuery terms:", query_terms)

    # GCIDE
    gcide = load_gcide()
    for t in query_terms:
        if t in gcide:
            print(f"\n---\nGCIDE definition for '{t}':\n")
            for d in gcide[t][:8]:
                print(" •", d)

    # Load verses
    all_verses = []
    for path in CORPORA:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                all_verses.extend(json.load(f))

    print("\nLoading verses...")
    print("Loaded", len(all_verses), "verses.")

    # Group by corpus
    by_corpus = defaultdict(list)
    for v in all_verses:
        # expects each verse to carry a "corpus" field
        by_corpus[v.get("corpus", "unknown")].append(v)

    # Score per corpus (simple literal count)
    for corpus, verses in by_corpus.items():
        scored = []

        for v in verses:
            text = v.get("text", "").lower()
            score = 0
            for t in query_terms:
                score += text.count(t)

            if score > 0:
                scored.append((score, v))

        scored.sort(key=lambda x: x[0], reverse=True)

        print("\n==============================")
        print("Corpus:", corpus)
        print("==============================\n")

        if not scored:
            print("(no matches)")
            continue

        for _, v in scored[:5]:
            book = v.get("work_title", "")
            ch = v.get("chapter", "")
            ve = v.get("verse", "")
            txt = v.get("text", "").strip()

            print(f"[{book}] {ch}:{ve}")
            print(txt)

            # optional Hebrew if present
            if "text_he" in v:
                print(v["text_he"])

            print()


if __name__ == "__main__":
    main()
