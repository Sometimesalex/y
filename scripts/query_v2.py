cat > scripts/query_v2.py <<'EOF'
#!/usr/bin/env python3

import json
import sys
import math
from pathlib import Path
from collections import defaultdict

from local_wordnet import LocalWordNet

ROOT = Path(__file__).resolve().parents[1]

CORPORA = [
    ("christianity_kjv", ROOT / "corpora" / "kjv" / "verses_enriched.json"),
    ("islam_quran_en", ROOT / "corpora" / "quran" / "verses_enriched.json"),
    ("judaism_tanakh_en", ROOT / "corpora" / "tanakh" / "verses_enriched.json"),
    ("buddhism_dhammapada_en", ROOT / "corpora" / "buddhism" / "verses_enriched.json"),
    ("hinduism_gita_en", ROOT / "corpora" / "hinduism" / "verses_enriched.json"),
]

GCIDE_PATH = ROOT / "corpora" / "GCIDE" / "gcide.json"
PROLOG_DIR = ROOT / "prolog"

TOP_N = 5

STOPWORDS = {
    "the","a","an","and","or","to","of","in","on","for","with","at","by",
    "is","are","was","were","be","been","being",
    "i","you","he","she","it","they","we",
    "how","what","when","where","why","should","will"
}

# -----------------------------

def tokenize(s):
    return [w.lower() for w in s.replace("?", "").replace(".", "").split() if w.lower() not in STOPWORDS]

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

# -----------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"question\"")
        return

    query = sys.argv[1]
    print("\nAsking:", query)

    terms = tokenize(query)
    print("Query terms:", terms)

    # GCIDE (optional)
    if GCIDE_PATH.exists():
        try:
            with open(GCIDE_PATH) as f:
                gcide = json.load(f)
            for t in terms:
                if t in gcide:
                    print(f"\n---\nGCIDE definition for '{t}':\n")
                    for g in gcide[t][:5]:
                        print(" •", g)
        except:
            pass

    # WordNet
    expanded = set(terms)
    try:
        wn = LocalWordNet(PROLOG_DIR)
        expanded = set(wn.expand_terms(terms))
        print("\nExpanded terms:", sorted(expanded))
    except Exception as e:
        print("\nWordNet skipped (non-fatal):", e)

    # Load corpora
    corpora = []
    for name, path in CORPORA:
        if path.exists():
            with open(path) as f:
                corpora.append((name, json.load(f)))

    all_verses = []
    for cname, verses in corpora:
        for v in verses:
            v["_corpus"] = cname
            all_verses.append(v)

    print(f"Loaded {len(all_verses)} verses.")

    # Build vocab ONLY from expanded terms
    vocab = {w:i for i,w in enumerate(expanded)}
    qv = vectorize(expanded, vocab)

    # Cheap lexical prefilter
    candidates = []
    for v in all_verses:
        text = v.get("text","").lower()
        if any(t in text for t in expanded):
            candidates.append(v)

    # Similarity
    scored = []
    for v in candidates:
        dv = vectorize(tokenize(v.get("text","")), vocab)
        s = cosine(qv, dv)
        if s > 0:
            scored.append((s, v))

    scored.sort(reverse=True, key=lambda x: x[0])

    by_corpus = defaultdict(list)
    for s,v in scored:
        by_corpus[v["_corpus"]].append(v)
        if len(by_corpus[v["_corpus"]]) >= TOP_N:
            continue

    for cname, verses in by_corpus.items():
        print("\n==============================")
        print("Corpus:", cname)
        print("==============================\n")
        for v in verses[:TOP_N]:
            ref = v.get("ref","")
            print(f"[{ref}] {v.get('text','')}\n")

# -----------------------------

if __name__ == "__main__":
    main()
EOF
