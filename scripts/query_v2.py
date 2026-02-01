#!/usr/bin/env python3
import json
import re
import sys
import math
from pathlib import Path
from collections import defaultdict

# Optional WordNet (kept non-fatal)
try:
    from prolog_reader import LocalWordNet  # your project module
except Exception:
    LocalWordNet = None

ROOT = Path(__file__).resolve().parents[1]

CORPORA = [
    ROOT / "corpora" / "kjv" / "verses_enriched.json",
    ROOT / "corpora" / "quran" / "verses_enriched.json",
    ROOT / "corpora" / "tanakh" / "verses_enriched.json",
]

GCIDE_PATH = ROOT / "corpora" / "GCIDE" / "gcide.json"

STOPWORDS = {
    # pronouns
    "i","me","my","mine","we","us","our","ours","you","your","yours",
    "he","him","his","she","her","hers","they","them","their","theirs","it","its",
    # auxiliaries / modals
    "is","am","are","was","were","be","been","being",
    "do","does","did","doing",
    "have","has","had","having",
    "should","would","could","may","might","must","shall","can","will",
    # common glue
    "the","a","an","and","or","of","to","in","on","for","with","as","by","at","from",
    # question words
    "how","what","why","when","where","who","which",
}

def tokenize(text: str):
    return re.findall(r"[a-z]+", text.lower())

def content_terms(query: str):
    toks = tokenize(query)
    # keep >1-char and not stopwords
    terms = [t for t in toks if len(t) > 1 and t not in STOPWORDS]
    # if we filtered EVERYTHING, fall back to >1-char (still avoids "i")
    if not terms:
        terms = [t for t in toks if len(t) > 1]
    # final fallback: if still empty, use original tokens (rare)
    if not terms:
        terms = toks
    return terms

def load_gcide():
    if not GCIDE_PATH.exists():
        return {}
    with open(GCIDE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # expected: { "word": ["def1", ...], ... }
    if isinstance(data, dict):
        return data
    return {}

def load_all_verses():
    all_by_corpus = defaultdict(list)

    for path in CORPORA:
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            verses = json.load(f)

        for v in verses:
            corpus = v.get("corpus", path.parent.name)
            all_by_corpus[corpus].append(v)

    return all_by_corpus

def build_index(verses):
    """
    Returns:
      postings: term -> list[(idx, tf)]
      doc_len: idx -> total tokens
      df: term -> doc frequency
    """
    postings = defaultdict(list)
    df = defaultdict(int)
    doc_len = {}

    for i, v in enumerate(verses):
        text = v.get("text", "") or ""
        toks = [t for t in tokenize(text) if len(t) > 1]
        doc_len[i] = len(toks)

        counts = defaultdict(int)
        for t in toks:
            counts[t] += 1

        for t, c in counts.items():
            postings[t].append((i, c))
            df[t] += 1

    return postings, doc_len, df

def score_query(terms, verses, postings, doc_len, df):
    """
    Simple TF-IDF cosine-ish scoring.
    """
    N = len(verses)
    scores = defaultdict(float)

    # query term weights
    q_counts = defaultdict(int)
    for t in terms:
        q_counts[t] += 1

    for t, q_tf in q_counts.items():
        if t not in postings:
            continue
        # IDF with smoothing
        idf = math.log((N + 1) / (df[t] + 1)) + 1.0
        for doc_i, tf in postings[t]:
            # normalized tf
            norm_tf = tf / max(1, doc_len.get(doc_i, 1))
            scores[doc_i] += (q_tf * idf) * (norm_tf * idf)

    return scores

def print_verse(v):
    work_title = v.get("work_title") or v.get("work") or ""
    chap = v.get("chapter", "")
    verse = v.get("verse", "")
    text = v.get("text", "").strip()

    # Optional Hebrew if present (Tanakh)
    text_he = v.get("text_he", None)

    if work_title:
        print(f"[{work_title}] {chap}:{verse}")
    else:
        print(f"{chap}:{verse}")
    print(text)
    if text_he:
        print(text_he)
    print()

def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question\"")
        sys.exit(1)

    q = " ".join(sys.argv[1:]).strip()
    print(f"\nAsking: {q}")

    # Terms (this MUST NOT zero everything out)
    terms = content_terms(q)
    print("\nQuery terms:", terms)

    # GCIDE (additive, never blocking)
    gcide = load_gcide()
    printed_any_gcide = False
    for t in sorted(set(terms)):
        defs = gcide.get(t)
        if defs:
            if not printed_any_gcide:
                print("\n---\n")
            printed_any_gcide = True
            print(f"GCIDE definition for '{t}':\n")
            for d in defs[:8]:
                print(" •", d)
            print()

    # WordNet (optional, non-fatal)
    if LocalWordNet is not None:
        try:
            print("Loading WordNet...")
            wn = LocalWordNet()
            wn.load_all(ROOT / "prolog")
            # You can hook wn expansions here later.
            print("WordNet ready.\n")
        except Exception as e:
            print("WordNet skipped (non-fatal):", e, "\n")

    # Load corpora
    print("Loading verses...")
    corpora_map = load_all_verses()
    total = sum(len(v) for v in corpora_map.values())
    print(f"Loaded {total} verses.\n")

    if not corpora_map:
        print("No corpora loaded. Check CORPORA paths.")
        sys.exit(1)

    # For EACH corpus: build index, score, print top 5 unique
    TOP_K = 5
    for corpus_name in sorted(corpora_map.keys()):
        verses = corpora_map[corpus_name]
        if not verses:
            continue

        print("=" * 30)
        print(f"Corpus: {corpus_name}")
        print("=" * 30)
        print()

        postings, doc_len, df = build_index(verses)
        scores = score_query(terms, verses, postings, doc_len, df)

        if not scores:
            print("(no matches)\n")
            continue

        # Sort by score desc
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # de-dupe exact verse identity (work/ch/verse/text)
        seen = set()
        out = 0
        for doc_i, sc in ranked:
            v = verses[doc_i]
            key = (
                v.get("work_title",""),
                v.get("chapter",""),
                v.get("verse",""),
                (v.get("text","") or "").strip()
            )
            if key in seen:
                continue
            seen.add(key)

            print_verse(v)
            out += 1
            if out >= TOP_K:
                break

        if out == 0:
            print("(no matches)\n")

if __name__ == "__main__":
    main()
