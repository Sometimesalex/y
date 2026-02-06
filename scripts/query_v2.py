#!/usr/bin/env python3

import json
import sys
import re
import time
import os
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
CORPORA_ROOT = ROOT / "corpora"
OUT_DIR = ROOT / "querycorpora"

WORD_RE = re.compile(r"[a-zA-Z']+")
TOP_N = 5


def tokenize(text):
    return WORD_RE.findall(text.lower())


def discover_corpora():
    # find EVERY verses_enriched.json anywhere under corpora/
    return list(CORPORA_ROOT.rglob("verses_enriched.json"))


def main():
    # Read query from argv or stdin
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip()
    else:
        query = sys.stdin.read().strip()

    if not query:
        os.makedirs(OUT_DIR, exist_ok=True)
        path = OUT_DIR / f"{int(time.time())}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"query": "", "results": []}, f, ensure_ascii=False, indent=2)
        print(str(path))
        return

    query_terms = tokenize(query)

    stop = {"the", "a", "an", "and", "or", "to", "of"}
    query_terms = [t for t in query_terms if t not in stop]

    corpus_files = discover_corpora()
    if not corpus_files:
        # still emit an empty result file
        os.makedirs(OUT_DIR, exist_ok=True)
        path = OUT_DIR / f"{int(time.time())}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"query": query, "results": []}, f, ensure_ascii=False, indent=2)
        print(str(path))
        return

    all_verses = []
    for path in corpus_files:
        try:
            with open(path, encoding="utf-8") as f:
                all_verses.extend(json.load(f))
        except Exception:
            pass

    by_corpus = defaultdict(list)
    for v in all_verses:
        by_corpus[v.get("corpus", "unknown")].append(v)

    results = []

    for corpus, verses in sorted(by_corpus.items()):
        scored = []

        for v in verses:
            text = (v.get("text", "") or "").lower()
            score = 0
            for t in query_terms:
                score += text.count(t)

            if score > 0:
                scored.append((score, v))

        scored.sort(key=lambda x: x[0], reverse=True)

        for score, v in scored[:TOP_N]:
            results.append({
                "corpus": corpus,
                "work_title": v.get("work_title", corpus),
                "chapter": v.get("chapter", ""),
                "verse": v.get("verse", ""),
                "text": (v.get("text", "") or "").strip(),
                "score": score
            })

    # Write to querycorpora/
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = int(time.time())
    out_path = OUT_DIR / f"{ts}.json"

    payload = {
        "query": query,
        "terms": query_terms,
        "results": results
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # If running in terminal, show JSON too
    if sys.stdout.isatty():
        print("\nWritten:", out_path)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        # Called from web_bridge: only emit path
        print(str(out_path))


if __name__ == "__main__":
    main()
