#!/usr/bin/env python3
"""
interpreter_v2.py

Query-conditioned, contrastive, stopword-suppressed interpreter for the Y project.

What it does (V2):
- Loads the most recent *.converted.json (or a provided --input file)
- Splits entries into:
    G+ : documents/entries that contain any query term
    G- : documents/entries that do NOT contain query terms (background)
- Builds weighted co-occurrence graphs from tokens (windowed)
- Computes discriminative "lift" for terms + edges: log( P(x|G+) / P(x|G-) )
- Prunes edges by lift + top-k per node to prevent saturation
- Extracts a "spine" (high-score connected component) and a high-score path approximation
- Computes "damage on removal" for top-lift terms (ablation test)

Output (no prose “answers”):
1) Evidence: top matching lines per corpus (+ match terms)
2) Top discriminative terms (lift)
3) Spine: nodes/edges with scores
4) Top necessary terms (damage)

Install: none (stdlib only).
Run:
  python -m interpreter.interpreter_v2 "what is a cat"
or:
  python interpreter/interpreter_v2.py "what is a cat" --input querycorpora/XYZ.converted.json
"""

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


# ----------------------------
# Tokenisation & stopwords
# ----------------------------

_BASIC_STOPWORDS = {
    # core function words
    "the", "a", "an", "and", "or", "but", "if", "then", "else",
    "of", "to", "in", "on", "at", "by", "for", "from", "with", "without",
    "is", "am", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "done",
    "have", "has", "had",
    "this", "that", "these", "those",
    "it", "its", "i", "you", "he", "she", "we", "they", "them", "him", "her", "us",
    "my", "your", "his", "hers", "our", "their", "thine", "thy", "thee", "thou",
    "not", "no", "nor",
    "who", "whom", "whose", "what", "why", "how", "where", "when",
    # common biblical-ish glue that often behaves like stopwords in your corpora
    "hath", "unto", "yea", "shall",
}

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z'\-]*")


def normalise_token(tok: str) -> str:
    tok = tok.strip().lower()
    tok = tok.replace("’", "'")
    return tok


def simple_tokenise(text: str) -> List[str]:
    return [normalise_token(m.group(0)) for m in _TOKEN_RE.finditer(text)]


# ----------------------------
# Data model
# ----------------------------

@dataclass(frozen=True)
class Entry:
    corpus: str
    ref: str
    text: str
    tokens: Tuple[str, ...]

    def contains_any(self, query_terms: Set[str]) -> bool:
        # use token set check; query terms already normalised
        tset = set(self.tokens)
        return any(q in tset for q in query_terms)


# ----------------------------
# Loading converted JSON
# ----------------------------

def _best_guess_entries(obj: Any) -> List[Dict[str, Any]]:
    """
    Try to locate "entries" in arbitrary converted JSON schemas.

    Supported shapes:
    - { "entries": [ ... ] }
    - { "corpora": { "name": [ ... ] } }
    - [ ... ]  (list of entries)
    """
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        if isinstance(obj.get("entries"), list):
            return obj["entries"]
        if isinstance(obj.get("items"), list):
            return obj["items"]
        corpora = obj.get("corpora")
        if isinstance(corpora, dict):
            out = []
            for cname, items in corpora.items():
                if isinstance(items, list):
                    for it in items:
                        if isinstance(it, dict):
                            it2 = dict(it)
                            it2.setdefault("corpus", cname)
                            out.append(it2)
                        else:
                            out.append({"corpus": cname, "text": str(it)})
            return out
    raise ValueError("Unrecognised converted JSON schema: cannot locate entries.")


def load_converted(path: Path) -> List[Entry]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw_entries = _best_guess_entries(raw)

    entries: List[Entry] = []
    for i, e in enumerate(raw_entries):
        if not isinstance(e, dict):
            e = {"text": str(e)}

        corpus = str(e.get("corpus") or e.get("source") or e.get("dataset") or "unknown")
        ref = str(e.get("ref") or e.get("id") or e.get("key") or e.get("verse") or f"entry:{i}")

        text = str(
            e.get("text")
            or e.get("line")
            or e.get("raw")
            or e.get("content")
            or e.get("value")
            or ""
        )

        toks = e.get("tokens") or e.get("terms") or e.get("tokenised") or None
        if isinstance(toks, list) and toks and all(isinstance(x, str) for x in toks):
            tokens = tuple(normalise_token(x) for x in toks)
        else:
            tokens = tuple(simple_tokenise(text))

        entries.append(Entry(corpus=corpus, ref=ref, text=text, tokens=tokens))

    return entries


def find_latest_converted(querycorpora_dir: Path) -> Path:
    candidates = sorted(querycorpora_dir.glob("*.converted.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No *.converted.json found in {querycorpora_dir}")
    return candidates[0]


# ----------------------------
# Graph building (co-occurrence)
# ----------------------------

Edge = Tuple[str, str]  # sorted (u, v)


def cooc_edges(tokens: List[str], window: int) -> Iterable[Edge]:
    n = len(tokens)
    for i in range(n):
        a = tokens[i]
        # look forward only
        for j in range(i + 1, min(n, i + 1 + window)):
            b = tokens[j]
            if a == b:
                continue
            u, v = (a, b) if a < b else (b, a)
            yield (u, v)


def filter_tokens(tokens: Iterable[str], stopwords: Set[str]) -> List[str]:
    out = []
    for t in tokens:
        t = normalise_token(t)
        if not t:
            continue
        if t in stopwords:
            continue
        # drop pure numbers / codes that look like coordinates or ids unless user wants them
        if re.fullmatch(r"\d+(\.\d+)?", t):
            continue
        out.append(t)
    return out


# ----------------------------
# Contrastive scoring (lift)
# ----------------------------

def safe_log(x: float) -> float:
    return math.log(x) if x > 0 else float("-inf")


def compute_lift(pos_counts: Counter, neg_counts: Counter, pos_total: int, neg_total: int, eps: float) -> Dict[str, float]:
    out: Dict[str, float] = {}
    keys = set(pos_counts.keys()) | set(neg_counts.keys())
    for k in keys:
        p = (pos_counts.get(k, 0) + eps) / (pos_total + eps * 2)
        n = (neg_counts.get(k, 0) + eps) / (neg_total + eps * 2)
        out[k] = safe_log(p / n)
    return out


# ----------------------------
# Spine extraction & damage
# ----------------------------

def build_adj_from_edges(edge_scores: Dict[Edge, float], min_lift: float, top_k: int) -> Dict[str, List[Tuple[str, float]]]:
    # build raw adjacency
    adj: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for (u, v), s in edge_scores.items():
        if s < min_lift:
            continue
        adj[u].append((v, s))
        adj[v].append((u, s))

    # prune per-node to top-k by edge score
    pruned: Dict[str, List[Tuple[str, float]]] = {}
    for node, nbrs in adj.items():
        nbrs_sorted = sorted(nbrs, key=lambda x: x[1], reverse=True)[:top_k]
        pruned[node] = nbrs_sorted
    return pruned


def connected_components(nodes: Set[str], adj: Dict[str, List[Tuple[str, float]]]) -> List[Set[str]]:
    seen: Set[str] = set()
    comps: List[Set[str]] = []
    for n in nodes:
        if n in seen:
            continue
        q = deque([n])
        comp = set()
        seen.add(n)
        while q:
            x = q.popleft()
            comp.add(x)
            for y, _s in adj.get(x, []):
                if y in nodes and y not in seen:
                    seen.add(y)
                    q.append(y)
        comps.append(comp)
    return comps


def component_score(comp: Set[str], term_lift: Dict[str, float], adj: Dict[str, List[Tuple[str, float]]]) -> float:
    score = 0.0
    for n in comp:
        score += term_lift.get(n, 0.0)
    # add edge scores once
    seen_edges = set()
    for u in comp:
        for v, s in adj.get(u, []):
            if v not in comp:
                continue
            a, b = (u, v) if u < v else (v, u)
            if (a, b) in seen_edges:
                continue
            seen_edges.add((a, b))
            score += s
    return score


def extract_spine(term_lift: Dict[str, float], adj: Dict[str, List[Tuple[str, float]]], max_nodes: int = 80) -> Set[str]:
    # candidate nodes = top by term lift that have adjacency
    candidates = [n for n in term_lift.keys() if n in adj]
    candidates = sorted(candidates, key=lambda n: term_lift.get(n, 0.0), reverse=True)[:max_nodes]
    nodes = set(candidates)
    if not nodes:
        return set()

    comps = connected_components(nodes, adj)
    # pick component with best total (node+edge) score
    best = max(comps, key=lambda c: component_score(c, term_lift, adj))
    return best


def best_path_in_spine(spine: Set[str], term_lift: Dict[str, float], adj: Dict[str, List[Tuple[str, float]]], max_len: int = 12) -> List[str]:
    """
    Greedy best path approximation:
    start from top node, repeatedly go to best scoring unvisited neighbor.
    """
    if not spine:
        return []
    start = max(spine, key=lambda n: term_lift.get(n, 0.0))
    path = [start]
    used = {start}
    cur = start
    while len(path) < max_len:
        options = [(nbr, es + term_lift.get(nbr, 0.0)) for nbr, es in adj.get(cur, []) if nbr in spine and nbr not in used]
        if not options:
            break
        nxt = max(options, key=lambda x: x[1])[0]
        path.append(nxt)
        used.add(nxt)
        cur = nxt
    return path


def damage_scores(spine: Set[str], term_lift: Dict[str, float], adj: Dict[str, List[Tuple[str, float]]], top_terms: List[str]) -> Dict[str, float]:
    """
    Damage = drop in (component size + component score) when node removed.
    """
    if not spine:
        return {t: 0.0 for t in top_terms}

    base_score = component_score(spine, term_lift, adj)
    base_size = len(spine)

    damages: Dict[str, float] = {}
    for t in top_terms:
        if t not in spine:
            damages[t] = 0.0
            continue
        remaining = set(spine)
        remaining.remove(t)
        if not remaining:
            damages[t] = base_score + base_size
            continue
        comps = connected_components(remaining, adj)
        # keep the largest surviving component (spine fragment)
        best_comp = max(comps, key=lambda c: (len(c), component_score(c, term_lift, adj)))
        new_score = component_score(best_comp, term_lift, adj)
        new_size = len(best_comp)
        # weighted drop
        damages[t] = (base_size - new_size) + (base_score - new_score)
    return damages


# ----------------------------
# Main
# ----------------------------

def parse_query_terms(q: str) -> Set[str]:
    toks = simple_tokenise(q)
    return set(toks)


def corpus_dominance_stopwords(entries: List[Entry], max_df: float, min_corpora_frac: float) -> Set[str]:
    """
    Compute tokens that behave like global scaffolding in your current dataset:
    - high document frequency overall (df/doc_count)
    - present in many corpora
    """
    doc_count = len(entries) if entries else 1
    df = Counter()
    corpora_presence = defaultdict(set)  # token -> set(corpora)
    for e in entries:
        unique = set(e.tokens)
        for t in unique:
            df[t] += 1
            corpora_presence[t].add(e.corpus)

    corpora_list = sorted({e.corpus for e in entries})
    corpora_n = max(1, len(corpora_list))

    sw = set()
    for t, d in df.items():
        if (d / doc_count) >= max_df and (len(corpora_presence[t]) / corpora_n) >= min_corpora_frac:
            sw.add(t)
    return sw


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="Natural language query; V2 uses terms to condition the graph.")
    ap.add_argument("--input", type=str, default="", help="Path to a *.converted.json file. If omitted, uses newest in ./querycorpora/")
    ap.add_argument("--querycorpora-dir", type=str, default="querycorpora", help="Directory containing *.converted.json files")
    ap.add_argument("--window", type=int, default=5, help="Co-occurrence window size")
    ap.add_argument("--seed", type=int, default=67, help="Random seed for background sampling")
    ap.add_argument("--eps", type=float, default=0.5, help="Smoothing epsilon for lift")
    ap.add_argument("--min-lift", type=float, default=0.3, help="Minimum edge lift to keep")
    ap.add_argument("--topk-edges", type=int, default=8, help="Top-K lifted edges kept per node")
    ap.add_argument("--max-evidence", type=int, default=5, help="Top matching lines per corpus to print")
    ap.add_argument("--max-terms", type=int, default=25, help="Top discriminative terms to print")
    ap.add_argument("--damage-n", type=int, default=30, help="How many top-lift terms to test for damage")
    ap.add_argument("--disable-dominance-stopwords", action="store_true", help="Disable corpus-dominance stopword layer")
    ap.add_argument("--dominance-max-df", type=float, default=0.65, help="Stopword if df >= this fraction of docs (overall)")
    ap.add_argument("--dominance-min-corpora-frac", type=float, default=0.70, help="Stopword if appears in >= this fraction of corpora")
    args = ap.parse_args(argv)

    query_terms = {normalise_token(t) for t in parse_query_terms(args.query)}
    if not query_terms:
        print("No query terms found after tokenisation.", file=sys.stderr)
        return 2

    random.seed(args.seed)

    # locate input
    if args.input:
        in_path = Path(args.input)
    else:
        in_path = find_latest_converted(Path(args.querycorpora_dir))

    if not in_path.exists():
        print(f"Input file not found: {in_path}", file=sys.stderr)
        return 2

    entries = load_converted(in_path)

    # stopwords: layer 1 (basic)
    stopwords = set(_BASIC_STOPWORDS)

    # stopwords: layer 2 (dominance)
    if not args.disable_dominance_stopwords:
        dom = corpus_dominance_stopwords(entries, max_df=args.dominance_max_df, min_corpora_frac=args.dominance_min_corpora_frac)
        stopwords |= dom

    # prepare entries with filtered tokens
    filtered_entries: List[Entry] = []
    for e in entries:
        toks = filter_tokens(e.tokens, stopwords)
        filtered_entries.append(Entry(corpus=e.corpus, ref=e.ref, text=e.text, tokens=tuple(toks)))

    # split into pos/neg
    pos = [e for e in filtered_entries if e.contains_any(query_terms)]
    neg = [e for e in filtered_entries if not e.contains_any(query_terms)]

    # if neg too small, sample background from full set excluding pos condition by random split
    if len(neg) < max(10, len(pos)):
        # fallback: random background sample from entries that don't match; else from all
        pool = [e for e in filtered_entries if e not in pos]
        neg = pool

    # evidence
    print(f"\nAsking: {args.query}")
    print(f"Query terms: {sorted(query_terms)}")
    print(f"Using converted file: {in_path}")
    print(f"Entries: total={len(filtered_entries)}  pos={len(pos)}  neg={len(neg)}")
    print()

    # group evidence by corpus
    pos_by_corpus: Dict[str, List[Entry]] = defaultdict(list)
    for e in pos:
        pos_by_corpus[e.corpus].append(e)

    print("=== EVIDENCE (per corpus, top matches) ===")
    for corpus in sorted(pos_by_corpus.keys()):
        items = pos_by_corpus[corpus][: args.max_evidence]
        print(f"\n--- {corpus} ({len(pos_by_corpus[corpus])} matches) ---")
        for it in items:
            # show what matched
            tset = set(it.tokens)
            matched = [t for t in sorted(query_terms) if t in tset]
            snippet = it.text.strip().replace("\n", " ")
            if len(snippet) > 240:
                snippet = snippet[:237] + "..."
            print(f"[{it.ref}] match={matched} :: {snippet}")
    if not pos_by_corpus:
        print("(No corpus had lexical matches after stopword filtering. Try --disable-dominance-stopwords or relax filtering.)")
    print()

    # term & edge counts
    def term_counter(entries_: List[Entry]) -> Counter:
        c = Counter()
        for e in entries_:
            c.update(e.tokens)
        return c

    def edge_counter(entries_: List[Entry], window: int) -> Counter:
        c = Counter()
        for e in entries_:
            toks = list(e.tokens)
            c.update(cooc_edges(toks, window))
        return c

    pos_term = term_counter(pos)
    neg_term = term_counter(neg)
    pos_term_total = sum(pos_term.values()) or 1
    neg_term_total = sum(neg_term.values()) or 1

    pos_edge = edge_counter(pos, args.window)
    neg_edge = edge_counter(neg, args.window)
    pos_edge_total = sum(pos_edge.values()) or 1
    neg_edge_total = sum(neg_edge.values()) or 1

    term_lift = compute_lift(pos_term, neg_term, pos_term_total, neg_term_total, args.eps)
    edge_lift = compute_lift(pos_edge, neg_edge, pos_edge_total, neg_edge_total, args.eps)

    # build adjacency from lifted edges
    adj = build_adj_from_edges(edge_lift, min_lift=args.min_lift, top_k=args.topk_edges)

    # compute spine
    spine = extract_spine(term_lift, adj, max_nodes=120)
    path = best_path_in_spine(spine, term_lift, adj, max_len=12)

    # top discriminative terms
    top_terms = [t for t, s in sorted(term_lift.items(), key=lambda x: x[1], reverse=True) if math.isfinite(s)]
    top_terms = [t for t in top_terms if t in pos_term][: args.max_terms]

    print("=== TOP DISCRIMINATIVE TERMS (lift) ===")
    for t in top_terms:
        print(f"{t:>20}  lift={term_lift[t]: .3f}  pos={pos_term.get(t,0)}  neg={neg_term.get(t,0)}")
    print()

    # spine report
    print("=== SPINE (high-score component) ===")
    print(f"spine_nodes={len(spine)}  path={' -> '.join(path) if path else '(none)'}")
    if spine:
        # show top nodes inside spine by lift
        spine_nodes_sorted = sorted(list(spine), key=lambda n: term_lift.get(n, 0.0), reverse=True)[:20]
        print("\nTop spine nodes:")
        for n in spine_nodes_sorted:
            print(f"  {n:>20}  lift={term_lift.get(n, 0.0): .3f}")

        # show top edges in spine by lift
        spine_edges: List[Tuple[Edge, float]] = []
        seen = set()
        for u in spine:
            for v, s in adj.get(u, []):
                if v not in spine:
                    continue
                a, b = (u, v) if u < v else (v, u)
                if (a, b) in seen:
                    continue
                seen.add((a, b))
                spine_edges.append(((a, b), s))
        spine_edges.sort(key=lambda x: x[1], reverse=True)

        print("\nTop spine edges:")
        for (u, v), s in spine_edges[:20]:
            print(f"  ({u}, {v})  lift={s: .3f}")
    else:
        print("(No spine found: likely not enough lifted edges. Try lowering --min-lift or disabling dominance stopwords.)")
    print()

    # damage / necessity
    damage_terms = top_terms[: max(5, min(args.damage_n, len(top_terms)))]
    damages = damage_scores(spine, term_lift, adj, damage_terms)
    ranked_damage = sorted(damages.items(), key=lambda x: x[1], reverse=True)

    print("=== TOP NECESSARY TERMS (damage on removal) ===")
    for t, d in ranked_damage[: min(20, len(ranked_damage))]:
        print(f"{t:>20}  damage={d: .3f}  lift={term_lift.get(t,0.0): .3f}")
    print()

    # debug summary
    print("=== DEBUG SUMMARY ===")
    print(f"unique_terms: pos={len(pos_term)} neg={len(neg_term)}")
    print(f"unique_edges: pos={len(pos_edge)} neg={len(neg_edge)}")
    print(f"adj_nodes={len(adj)}")
    # count lifted edges kept (approx)
    kept_edges = sum(len(v) for v in adj.values()) // 2
    print(f"kept_edges~={kept_edges}  (min_lift={args.min_lift}, topk_edges={args.topk_edges})")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
