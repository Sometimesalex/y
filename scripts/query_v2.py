#!/usr/bin/env python3

import json
import sys
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
CORPORA_ROOT = ROOT / "corpora"
GCIDE_PATH = ROOT / "corpora" / "GCIDE" / "gcide.json"
HUMAN_FLOW = ROOT / "corpora" / "human_flow" / "human_flow.txt"

WORD_RE = re.compile(r"[a-zA-Z']+")
TOP_N = 5


def tokenize(text):
    return WORD_RE.findall(text.lower())


def load_gcide():
    if not GCIDE_PATH.exists():
        return {}
    with open(GCIDE_PATH, encoding="utf-8") as f:
        return json.load(f)


# -----------------------------
# Human flow loader
# -----------------------------

human_flow_events = []

if HUMAN_FLOW.exists():
    with open(HUMAN_FLOW, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            try:
                t = int(parts[0])
            except:
                t = 0
            human_flow_events.append((t, parts[1:]))

    human_flow_events.sort(key=lambda x: x[0])

print("Loaded human_flow:", len(human_flow_events))


def human_context_around(year, window=300):
    lo = year - window
    hi = year + window
    out = []
    for t, row in human_flow_events:
        if t < lo:
            continue
        if t > hi:
            break
        out.append((t, row))
    return out


def discover_corpora():
    return list(CORPORA_ROOT.rglob("verses_enriched.json"))


def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question\"")
        sys.exit(1)

    query = sys.argv[1].lower()
    query_terms = tokenize(query)

    stop = {"the", "a", "an", "and", "or", "to", "of"}
    query_terms = [t for t in query_terms if t not in stop]

    print("\nAsking:", query)
    print("Query terms:", query_terms)

    # GCIDE
    gcide = load_gcide()
    for t in query_terms:
        if t in gcide:
            print(f"\n---\nGCIDE definition for '{t}':\n")
            for d in gcide[t][:6]:
                print(" •", d)

    corpus_files = discover_corpora()

    if not corpus_files:
        print("No corpora found.")
        sys.exit(1)

    all_verses = []

    for path in corpus_files:
        try:
            with open(path, encoding="utf-8") as f:
                all_verses.extend(json.load(f))
        except Exception as e:
            print("Failed loading:", path, e)

    print("\nLoaded", len(all_verses), "verses total.")

    by_corpus = defaultdict(list)
    for v in all_verses:
        by_corpus[v.get("corpus", "unknown")].append(v)

    # -----------------------------
    # Scripture results
    # -----------------------------

    for corpus, verses in sorted(by_corpus.items()):
        scored = []

        for v in verses:
            text = v.get("text", "").lower()
            score = 0
            for t in query_terms:
                score += text.count(t)
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

    # -----------------------------
    # GLOBAL HUMAN FLOW CONTEXT
    # -----------------------------

    hc = human_context_around(-500, window=300)

    if hc:
        print("\n==============================")
        print("GLOBAL HUMAN FLOW CONTEXT (-500 ±300)")
        print("==============================\n")
        for t, row in hc[:25]:
            print(t, row)


if __name__ == "__main__":
    main()
