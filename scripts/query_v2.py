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


def tokenize(text):
    return WORD_RE.findall(text.lower())


def discover_corpora():
    return list(CORPORA_ROOT.rglob("verses_enriched.json"))


def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:]).strip()
    else:
        query = sys.stdin.read().strip()

    query_terms = tokenize(query)
    stop = {"the","a","an","and","or","to","of"}
    query_terms = [t for t in query_terms if t not in stop]

    corpus_files = discover_corpora()

    corpora = defaultdict(list)

    for path in corpus_files:
        try:
            verses = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue

        for v in verses:
            text = (v.get("text","") or "").lower()
            score = sum(text.count(t) for t in query_terms)

            if score > 0:
                corpora[v.get("corpus","unknown")].append({
                    "work_title": v.get("work_title",""),
                    "chapter": v.get("chapter",""),
                    "verse": v.get("verse",""),
                    "text": v.get("text",""),
                    "score": score
                })

    payload = {
        "query": query,
        "terms": query_terms,
        "corpora": corpora
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    ts = int(time.time())
    out_path = OUT_DIR / f"{ts}.json"

    with open(out_path,"w",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,indent=2)

    if sys.stdout.isatty():
        print("\nWritten:", out_path)
        print(json.dumps(payload,ensure_ascii=False,indent=2))
    else:
        print(str(out_path))


if __name__ == "__main__":
    main()
