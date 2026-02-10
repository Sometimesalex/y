"""
interpreter_v2.py — Structure-first interpreter with semantic probe support
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Set

from interpreter.probe import SemanticProbe, print_probe_report


BASIC_STOPWORDS = {
    "the", "and", "is", "of", "to", "in", "a", "that", "it", "as",
    "for", "with", "was", "were", "be", "by", "on", "this", "are",
}


class Entry:
    def __init__(self, corpus: str, ref: str, text: str):
        self.corpus = corpus
        self.ref = ref
        self.text = text
        self.tokens = self._tokenize(text)

    def _tokenize(self, text: str) -> Set[str]:
        return {
            t.lower()
            for t in text.replace("\n", " ").split()
            if t.isalpha()
        }

    def contains_any(self, terms: Set[str]) -> bool:
        return bool(self.tokens & terms)


def load_converted(path: Path) -> List[Entry]:
    data = json.loads(path.read_text())
    entries: List[Entry] = []

    for corpus, items in data.get("corpora", {}).items():
        for it in items:
            text = it.get("text") or ""
            ref = it.get("ref") or ""
            entries.append(Entry(corpus, ref, text))

    return entries


def parse_query_terms(q: str) -> Set[str]:
    return {t.lower() for t in q.split() if t.isalpha()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--converted", default="querycorpora/1770750681.converted.json")
    ap.add_argument("--probe", action="store_true", help="Enable GCIDE semantic probe")
    ap.add_argument("--probe-report", action="store_true", help="Print probe report")
    args = ap.parse_args(argv)

    query_terms = parse_query_terms(args.query)
    stopwords = set(BASIC_STOPWORDS)

    filtered_query = {t for t in query_terms if t not in stopwords}

    entries = load_converted(Path(args.converted))

    probe_terms: Set[str] = set()
    if args.probe:
        probe = SemanticProbe(stopwords=stopwords)
        result = probe.probe(query_terms)
        probe_terms = result.expanded_terms
        if args.probe_report:
            print_probe_report(result)

    match_terms = filtered_query | probe_terms

    pos = [e for e in entries if e.contains_any(match_terms)]
    neg = [e for e in entries if not e.contains_any(match_terms)]

    print(f"\nAsking: {args.query}")
    print(f"Query terms: {sorted(filtered_query)}")
    if args.probe:
        print(f"Probe terms: {sorted(list(probe_terms))[:20]}")
    print(f"Entries: total={len(entries)} pos={len(pos)} neg={len(neg)}\n")

    by_corpus = defaultdict(list)
    for e in pos:
        by_corpus[e.corpus].append(e)

    print("=== EVIDENCE (per corpus) ===")
    if not by_corpus:
        print("(No matches — corpus does not embody this object)")
        return 0

    for corpus, items in sorted(by_corpus.items()):
        print(f"\n--- {corpus} ({len(items)} matches) ---")
        for e in items[:5]:
            matched = sorted(e.tokens & match_terms)
            snippet = e.text.replace("\n", " ")
            print(f"[{e.ref}] match={matched} :: {snippet[:240]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
