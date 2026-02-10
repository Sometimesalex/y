*** a/interpreter/interpreter_v2.py
--- b/interpreter/interpreter_v2.py
@@
 from __future__ import annotations
 
 import argparse
 import json
 import math
 import os
 import random
 import re
 import sys
 from collections import Counter, defaultdict, deque
 from dataclasses import dataclass
 from pathlib import Path
 from typing import Dict, Iterable, List, Optional, Set, Tuple, Any
+
+# NEW: semantic probe layer (GCIDE-as-hypothesis, not authority)
+from interpreter.probe import SemanticProbe, format_probe_report
 
@@
 def main(argv: Optional[List[str]] = None) -> int:
     ap = argparse.ArgumentParser()
     ap.add_argument("query", help="Natural language query; V2 uses terms to condition the graph.")
@@
     ap.add_argument("--disable-dominance-stopwords", action="store_true", help="Disable corpus-dominance stopword layer")
     ap.add_argument("--dominance-max-df", type=float, default=0.65, help="Stopword if df >= this fraction of docs (overall)")
     ap.add_argument("--dominance-min-corpora-frac", type=float, default=0.70, help="Stopword if appears in >= this fraction of corpora")
+
+    # NEW: probe controls
+    ap.add_argument("--probe", choices=["off", "gcide"], default="off",
+                    help="Enable semantic probe expansion (gcide). Probe generates hypotheses; corpora still answer.")
+    ap.add_argument("--probe-max-traits", type=int, default=16,
+                    help="Max trait tokens extracted per query term from GCIDE.")
+    ap.add_argument("--probe-include-original", action="store_true",
+                    help="Keep original query terms even if they are stopwords (not recommended).")
+    ap.add_argument("--probe-report", action="store_true",
+                    help="Print probe report (definitions + extracted traits).")
     args = ap.parse_args(argv)
 
-    query_terms = {normalise_token(t) for t in parse_query_terms(args.query)}
+    raw_query_terms = {normalise_token(t) for t in parse_query_terms(args.query)}
+    query_terms = set(raw_query_terms)
     if not query_terms:
         print("No query terms found after tokenisation.", file=sys.stderr)
         return 2
@@
     # stopwords: layer 1 (basic)
     stopwords = set(_BASIC_STOPWORDS)
 
     # stopwords: layer 2 (dominance)
@@
         dom = corpus_dominance_stopwords(entries, max_df=args.dominance_max_df, min_corpora_frac=args.dominance_min_corpora_frac)
         stopwords |= dom
 
+    # IMPORTANT: don't let stopwords erase the question unless explicitly requested
+    if not args.probe_include_original:
+        query_terms = {t for t in query_terms if t not in stopwords}
+
+    # NEW: probe expansion (adds trait tokens as retrieval hints)
+    probe_terms: Set[str] = set()
+    if args.probe == "gcide":
+        probe = SemanticProbe(
+            provider=None,  # AutoGCIDEProvider
+            stopwords=stopwords,
+            max_traits_per_term=args.probe_max_traits,
+        )
+        # probe against the *raw* query terms (before stopword filtering),
+        # because dictionary definitions can help when the user typed only glue words.
+        pr = probe.probe(raw_query_terms)
+        probe_terms = {t for t in pr.expanded_terms if t and t not in stopwords}
+        if args.probe_report:
+            print("\n=== PROBE REPORT (GCIDE -> traits) ===")
+            print(format_probe_report(pr))
+            print()
+
+    expanded_terms = set(query_terms) | set(probe_terms)
+
     # prepare entries with filtered tokens
     filtered_entries: List[Entry] = []
     for e in entries:
@@
     # split into pos/neg
-    pos = [e for e in filtered_entries if e.contains_any(query_terms)]
-    neg = [e for e in filtered_entries if not e.contains_any(query_terms)]
+    # use expanded terms for matching (probe terms are only retrieval hints)
+    pos = [e for e in filtered_entries if e.contains_any(expanded_terms)]
+    neg = [e for e in filtered_entries if not e.contains_any(expanded_terms)]
 
@@
     print(f"\nAsking: {args.query}")
-    print(f"Query terms: {sorted(query_terms)}")
+    print(f"Query terms (filtered): {sorted(query_terms)}")
+    if args.probe == "gcide":
+        print(f"Probe terms added: {sorted(list(probe_terms))[:40]}{' ...' if len(probe_terms) > 40 else ''}")
+    print(f"Match terms used: {sorted(list(expanded_terms))[:40]}{' ...' if len(expanded_terms) > 40 else ''}")
     print(f"Using converted file: {in_path}")
     print(f"Entries: total={len(filtered_entries)}  pos={len(pos)}  neg={len(neg)}")
     print()
@@
     print("=== EVIDENCE (per corpus, top matches) ===")
     for corpus in sorted(pos_by_corpus.keys()):
         items = pos_by_corpus[corpus][: args.max_evidence]
         print(f"\n--- {corpus} ({len(pos_by_corpus[corpus])} matches) ---")
         for it in items:
             # show what matched
             tset = set(it.tokens)
-            matched = [t for t in sorted(query_terms) if t in tset]
+            matched = [t for t in sorted(expanded_terms) if t in tset]
             snippet = it.text.strip().replace("\n", " ")
             if len(snippet) > 240:
                 snippet = snippet[:237] + "..."
             print(f"[{it.ref}] match={matched} :: {snippet}")
     if not pos_by_corpus:
-        print("(No corpus had lexical matches after stopword filtering. Try --disable-dominance-stopwords or relax filtering.)")
+        print("(No corpus had lexical matches. Try --probe gcide --probe-report, or relax stopwords / use a different converted file.)")
     print()
