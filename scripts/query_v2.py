cat > scripts/query_v2.py <<'EOF'
#!/usr/bin/env python3

import json
import sys
import math
import re
from pathlib import Path
from collections import defaultdict

from local_wordnet import LocalWordNet


ROOT = Path(__file__).resolve().parents[1]

CORPORA = [
    ROOT / "corpora" / "kjv" / "verses_enriched.json",
    ROOT / "corpora" / "quran" / "verses_enriched.json",
    ROOT / "corpora" / "tanakh" / "verses_enriched.json",
    ROOT / "corpora" / "buddhism" / "verses_enriched.json",
    ROOT / "corpora" / "hinduism" / "verses_enriched.json",
]

GCIDE_PATH = ROOT / "corpora" / "GCIDE" / "gcide.json"

TOP_N = 5

STOPWORDS = {
    "the","a","an","and","or","but","if","then","else",
    "is","are","was","were","be","been","being",
    "of","to","in","on","for","with","as","by","from",
    "that","this","these","those",
    "i","you","he","she","it","we","they","me","him","her","us","them",
    "my","your","his","hers","its","our","their",
    "what","when","where","why","how","who","whom","which",
    "will","shall","should","would","could","may","might","must",
}


def tokenize(s):
    words = re.findall(r"[a-zA-Z']+", s.lower())
    return [w for w in words if w not in STOPWORDS]


def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def vectorize(tokens, vocab):
    v = [0]*len(vocab)
    for t in tokens:
        if t in vocab:
            v[vocab[t]] += 1
    return v


def load_gcide():
    if not GCIDE_PATH.exists():
        return {}
    with open(GCIDE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {k.lower(): v for k, v in data.items()}


def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question\"")
        sys.exit(1)

    query = sys.argv[1]
    print("\nAsking:", query)

    query_terms = tokenize(query)
    print("\nQuery terms:", query_terms)

    # GCIDE
    gcide = load_gcide()
    if gcide:
        print("GCIDE entries:", len(gcide))
        for t in query_terms:
            if t in gcide:
                print(f"\n---\nGCIDE definition for '{t}':\n")
                for d in gcide[t][:5]:
                    print(" •", d)

    # WordNet
    try:
        wn = LocalWordNet()
        expanded = set(query_terms)
        for t in query_terms:
            expanded |= set(wn.expand(t))
        query_terms = list(expanded)
        print("\nExpanded terms:", sorted(query_terms))
    except Exception as e:
        print("\nWordNet skipped (non-fatal):", e)

    # Load verses
    verses = []
    for p in CORPORA:
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            verses += json.load(f)

    print("Loaded", len(verses), "verses.")

    docs = []
    for v in verses:
        toks = tokenize(v.get("text",""))
        docs.append((v, toks))

    vocab = {}
    for _, toks in docs:
        for t in toks:
            if t not in vocab:
                vocab[t] = len(vocab)

    qv = vectorize(query_terms, vocab)

    scored = []
    for v, toks in docs:
        dv = vectorize(toks, vocab)
        s = cosine(qv, dv)
        if s > 0:
            scored.append((s, v))

    scored.sort(reverse=True, key=lambda x: x[0])

    grouped = defaultdict(list)
    for s, v in scored[:200]:
        grouped[v["corpus"]].append(v)

    for corpus, items in grouped.items():
        print("\n==============================")
        print("Corpus:", corpus)
        print("==============================\n")
        for v in items[:TOP_N]:
            ref = v.get("work_title", v.get("work",""))
            chap = v.get("chapter","")
            vs = v.get("verse","")
            print(f"[{ref}] {chap}:{vs}")
            print(v["text"])
            print()

if __name__ == "__main__":
    main()
EOF
