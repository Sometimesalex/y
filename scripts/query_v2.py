#!/usr/bin/env python3

import json
import sys
import math
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


TOKEN_RE = re.compile(r"[a-zA-Z']+")


def tokenize(text):
    return [t.lower() for t in TOKEN_RE.findall(text)]


def load_gcide():
    if not GCIDE_PATH.exists():
        return {}

    with open(GCIDE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    out = {}
    for k, v in data.items():
        if isinstance(v, list):
            out[k.lower()] = v
    print("GCIDE entries:", len(out))
    return out


def load_corpora():
    all_rows = []

    for path in CORPORA:
        if not path.exists():
            continue

        with open(path, encoding="utf-8") as f:
            rows = json.load(f)

        all_rows.extend(rows)

    print("Loaded", len(all_rows), "verses.")
    return all_rows


def build_index(rows):
    tf = []
    df = defaultdict(int)

    for r in rows:
        toks = tokenize(r.get("text", ""))
        counts = defaultdict(int)
        for t in toks:
            counts[t] += 1
        tf.append(counts)
        for t in counts:
            df[t] += 1

    return tf, df


def score_query(qtokens, rows, tf, df):
    N = len(rows)
    scores = []

    for i, r in enumerate(rows):
        s = 0.0
        for t in qtokens:
            if t in tf[i]:
                idf = math.log((N + 1) / (df[t] + 1))
                s += tf[i][t] * idf
        scores.append(s)

    return scores


def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question\"")
        sys.exit(1)

    query = sys.argv[1].strip().lower()
    print("\nAsking:", query)

    qtokens = tokenize(query)
    if not qtokens:
        print("No usable tokens.")
        sys.exit(0)

    print("\nQuery terms:", qtokens)

    # GCIDE
    gcide = load_gcide()
    for t in qtokens:
        if t in gcide:
            print(f"\n---\nGCIDE definition for '{t}':\n")
            for d in gcide[t]:
                print(" •", d)

    # WordNet (loaded for future expansion)
    try:
        print("\nLoading WordNet...")
        wn = LocalWordNet()
        wn.load_all(ROOT / "prolog")
        print("WordNet ready.\n")
    except Exception as e:
        print("\nWordNet skipped (non-fatal):", e, "\n")

    # Load corpora
    rows = load_corpora()

    tf, df = build_index(rows)
    scores = score_query(qtokens, rows, tf, df)

    # Group by corpus
    grouped = defaultdict(list)
    for r, s in zip(rows, scores):
        if s > 0:
            grouped[r["corpus"]].append((s, r))

    TOP_N = 5

    for corpus in sorted(grouped.keys()):
        print("\n==============================")
        print("Corpus:", corpus)
        print("==============================\n")

        hits = sorted(grouped[corpus], key=lambda x: x[0], reverse=True)[:TOP_N]

        for score, r in hits:
            ref = f"[{r.get('work_title','')}] {r.get('chapter')}:{r.get('verse')}"
            print(ref)
            print(r.get("text", ""))

            if "text_he" in r:
                print(r["text_he"])

            print("")

    if not grouped:
        print("\nNo matches found.")


if __name__ == "__main__":
    main()
