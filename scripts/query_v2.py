#!/usr/bin/env python3

import json
import sys
import re
from pathlib import Path
from collections import defaultdict

from prolog_reader import LocalWordNet
from archaic_map import normalize_archaic

ROOT = Path(__file__).resolve().parents[1]

KJV_PATH = ROOT / "corpora/kjv/verses_enriched.json"
QURAN_PATH = ROOT / "corpora/quran/verses_enriched.json"
GCIDE_PATH = ROOT / "corpora/GCIDE/gcide.json"

word_re = re.compile(r"[a-z]+")

STOPWORDS = set("""
what do you about think is are was were the a an and or of to in on for with as by at from
he she they them we us i me my your his her their our should
""".split())


def words(t):
    return word_re.findall(t.lower())


def load_json(p):
    if not p.exists():
        return []
    return json.loads(p.read_text())


def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question here\"")
        sys.exit(1)

    q = " ".join(sys.argv[1:])
    print("\nAsking:", q)

    # ---------------- LOAD VERSES ----------------

    print("Loading verses...")
    verses = []
    verses += load_json(KJV_PATH)
    verses += load_json(QURAN_PATH)
    print(f"Loaded {len(verses)} verses.")

    # tokenize once
    VERSE_WORDS = [normalize_archaic(words(v["text"])) for v in verses]

    VOCAB = set()
    for w in VERSE_WORDS:
        VOCAB.update(w)

    # ---------------- GCIDE ----------------

    GCIDE = {}
    if GCIDE_PATH.exists():
        print("Loading GCIDE...")
        GCIDE = json.loads(GCIDE_PATH.read_text())
        GCIDE = {k.lower(): v for k, v in GCIDE.items()}
        print("GCIDE entries:", len(GCIDE))

    # ---------------- WORDNET ----------------

    print("Loading WordNet...")
    wn = LocalWordNet()   # <<< FIXED HERE

    # build synset->words
    SYNSET_TO_WORDS = defaultdict(set)
    for w, senses in wn.senses.items():
        for s in senses:
            SYNSET_TO_WORDS[s["synset"]].add(w)

    # global baseline
    GLOBAL_SENSES = defaultdict(int)
    for wlist in VERSE_WORDS:
        for w in wlist:
            for m in wn.lookup(w):
                GLOBAL_SENSES[m["synset"]] += 1

    GLOBAL_TOTAL = float(sum(GLOBAL_SENSES.values()) or 1)

    # ---------------- QUERY ----------------

    raw_terms = [w for w in words(q) if w not in STOPWORDS]

    print("\nQuery terms:", raw_terms)

    # GCIDE first (modern meaning exposure)
    for t in raw_terms:
        if t in GCIDE:
            print(f"\nGCIDE definition for '{t}':\n")
            for d in GCIDE[t][:5]:
                print(" •", d.strip())

    # ---------------- SCORE PER CORPUS ----------------

    by_corpus = defaultdict(list)

    for v, wlist in zip(verses, VERSE_WORDS):
        if not any(t in wlist for t in raw_terms):
            continue

        LOCAL = defaultdict(int)
        for tok in wlist:
            if tok in raw_terms:
                for m in wn.lookup(tok):
                    LOCAL[m["synset"]] += 1

        local_total = sum(LOCAL.values()) or 1.0

        score = 0.0
        for syn, lc in LOCAL.items():
            gc = GLOBAL_SENSES.get(syn, 1)
            score += (lc / local_total) - (gc / GLOBAL_TOTAL)

        vv = dict(v)
        vv["score"] = score
        by_corpus[v["corpus"]].append(vv)

    if not by_corpus:
        print("\nNo corpus matches.")
        return

    # ---------------- OUTPUT (ADDITIVE) ----------------

    for corpus, items in by_corpus.items():
        print("\n==============================")
        print("Corpus:", corpus)
        print("==============================")

        ranked = sorted(items, key=lambda x: -x["score"])

        seen = set()
        out = []

        for r in ranked:
            key = (r["work"], r["chapter"], r["verse"])
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
            if len(out) >= 5:
                break

        for v in out:
            print(f"\n[{v.get('work_title','')}] {v['chapter']}:{v['verse']}")
            print(v["text"])


if __name__ == "__main__":
    main()
