#!/usr/bin/env python3

import json
import sys
import math
from pathlib import Path
from collections import defaultdict

from local_wordnet import LocalWordNet


ROOT = Path(__file__).resolve().parents[1]

CORPORA = [
    ROOT / "corpora" / "kjv" / "verses_enriched.json",
    ROOT / "corpora" / "quran" / "verses_enriched.json",
    ROOT / "corpora" / "tanakh" / "verses_enriched.json",
]

GCIDE_PATH = ROOT / "corpora" / "GCIDE" / "gcide.json"

TOP_N = 5


def tokenize(s):
    return [w.lower() for w in s.replace("?", "").replace(".", "").split()]


def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def vectorize(tokens, vocab):
    v = [0.0] * len(vocab)
    idx = {w: i for i, w in enumerate(vocab)}
    for t in tokens:
        if t in idx:
            v[idx[t]] += 1.0
    return v


def load_gcide():
    if not GCIDE_PATH.exists():
        return {}
    with open(GCIDE_PATH, encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question\"")
        sys.exit(1)

    query = sys.argv[1]
    print("\nAsking:", query)

    print("Loading verses...")
    all_corpora = []
    for p in CORPORA:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                all_corpora.append(json.load(f))

    total = sum(len(c) for c in all_corpora)
    print("Loaded", total, "verses.")

    print("Loading GCIDE...")
    gcide = load_gcide()
    print("GCIDE entries:", len(gcide))

    print("Loading WordNet...")
    wn = LocalWordNet()
    print("WordNet ready.\n")

    q_tokens = tokenize(query)

    # print GCIDE definitions if available
    for t in q_tokens:
        if t in gcide:
            print(f"\nGCIDE definition for '{t}':\n")
            for d in gcide[t][:5]:
                print(" •", d)
            break

    print("\nQuery terms:", q_tokens)

    # process each corpus independently
    for corpus in all_corpora:
        if not corpus:
            continue

        corpus_name = corpus[0].get("corpus", "unknown")

        print("\n==============================")
        print("Corpus:", corpus_name)
        print("==============================\n")

        texts = [v["text"] for v in corpus]
        tokenized = [tokenize(t) for t in texts]

        vocab = sorted(set(w for toks in tokenized for w in toks))
        q_vec = vectorize(q_tokens, vocab)

        scored = []
        for verse, toks in zip(corpus, tokenized):
            v_vec = vectorize(toks, vocab)
            s = cosine(q_vec, v_vec)
            if s > 0:
                scored.append((s, verse))

        scored.sort(key=lambda x: x[0], reverse=True)

        top = scored[:TOP_N]

        if not top:
            print("(no matches)")
            continue

        for _, v in top:
            ref = f"[{v.get('work_title','')}] {v.get('chapter')}:{v.get('verse')}"
            print(ref)
            print(v["text"])
            if "text_he" in v:
                print(v["text_he"])
            print()


if __name__ == "__main__":
    main()
