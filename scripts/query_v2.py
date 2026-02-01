#!/usr/bin/env python3

import json
import sys
import math
import re
from pathlib import Path
from collections import defaultdict

# Optional WordNet
try:
    from local_wordnet import LocalWordNet
except Exception:
    LocalWordNet = None

ROOT = Path(__file__).resolve().parents[1]

CORPORA = [
    ROOT / "corpora" / "christianity_kjv" / "verses_enriched.json",
    ROOT / "corpora" / "islam_quran" / "verses_enriched.json",
    ROOT / "corpora" / "judaism_tanakh" / "verses_enriched.json",
    ROOT / "corpora" / "buddhism" / "verses_enriched.json",
    ROOT / "corpora" / "hinduism" / "verses_enriched.json",
]

GCIDE_PATH = ROOT / "corpora" / "GCIDE" / "gcide.json"

STOPWORDS = {
    "the","a","an","and","or","of","to","is","are","was","were","be","been",
    "i","you","he","she","it","we","they","what","how","when","where","why",
    "should","would","could","am","here"
}

TOP_N = 5


def normalize(s):
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower())


def tokenize(s):
    return [w for w in normalize(s).split() if w and w not in STOPWORDS]


def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def vectorize(tokens, vocab):
    v = [0.0] * len(vocab)
    idx = {w:i for i,w in enumerate(vocab)}
    for t in tokens:
        if t in idx:
            v[idx[t]] += 1.0
    return v


def load_gcide():
    if not GCIDE_PATH.exists():
        return {}
    with open(GCIDE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def print_gcide(gcide, terms):
    for t in terms:
        if t in gcide:
            print(f"\n---\nGCIDE definition for '{t}':\n")
            for d in gcide[t][:5]:
                print(" •", d)


def load_corpus(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question\"")
        sys.exit(1)

    query = sys.argv[1]
    print("\nAsking:", query)

    query_terms = tokenize(query)
    print("Query terms:", query_terms)

    gcide = load_gcide()
    if gcide:
        print_gcide(gcide, query_terms)

    expanded = set(query_terms)

    # WordNet expansion (optional)
    if LocalWordNet:
        try:
            wn = LocalWordNet(str(ROOT / "prolog"))
            wn_terms = set()
            for t in query_terms:
                try:
                    wn_terms |= set(wn.expand(t, depth=1))
                except Exception:
                    pass
            expanded |= wn_terms
            print("\nExpanded terms:", sorted(expanded))
        except Exception as e:
            print("\nWordNet skipped (non-fatal):", e)

    terms = list(expanded)

    print("Searching with terms:", terms)

    all_docs = []
    corpus_map = {}

    for cpath in CORPORA:
        if not cpath.exists():
            continue
        cname = cpath.parent.name
        verses = load_corpus(cpath)
        corpus_map[cname] = verses
        for v in verses:
            all_docs.append((cname, v))

    print("Loaded", len(all_docs), "verses.")

    # Build vocab
    vocab = set()
    doc_tokens = []
    for cname, v in all_docs:
        toks = tokenize(v.get("text",""))
        doc_tokens.append(toks)
        vocab |= set(toks)

    vocab = sorted(vocab)

    qv = vectorize(terms, vocab)

    scored = defaultdict(list)

    for (cname, v), toks in zip(all_docs, doc_tokens):
        dv = vectorize(toks, vocab)
        s = cosine(qv, dv)

        # ALSO allow literal fallback
        literal = any(t in normalize(v.get("text","")) for t in terms)

        if s > 0 or literal:
            scored[cname].append((s, v))

    for cname in scored:
        scored[cname].sort(key=lambda x: x[0], reverse=True)

    for cname, items in scored.items():
        print("\n==============================")
        print("Corpus:", cname)
        print("==============================\n")

        for s, v in items[:TOP_N]:
            ref = v.get("ref","")
            txt = v.get("text","").strip()
            print(f"[{ref}] {txt}\n")


if __name__ == "__main__":
    main()
EOF
