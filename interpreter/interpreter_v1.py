from __future__ import annotations
import sys
import json
from pathlib import Path
from typing import List
from collections import defaultdict

from interpreter.semantic_types import SeedParams, ClusterParams, SpineParams, MCurrent
from interpreter.graph import InteractionGraph
from interpreter.essence import QueryV2Adapter, build_semantic_essence_from_hits
from interpreter.builder import add_essence_to_graph, add_cross_corpus_overlap_edges
from interpreter.cluster import select_seeds, grow_cluster_from_seed, merge_clusters, compute_bridges
from interpreter.spines import build_spines, choose_spines_for_output
from interpreter.debug import cluster_card, spine_debug, ascii_cluster_adjacency

# -----------------------------
# Threshold modes
# -----------------------------

BOOT = dict(seed_min=1.0, seed_sep=1, edge_min=0.05, core_size=3)
TIGHT = dict(seed_min=3.0, seed_sep=2, edge_min=0.55, core_size=7)

# -----------------------------
# Paths
# -----------------------------

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "Interpreteroutput"
OUT_FILE = OUT_DIR / "interpreter_result.json"

def _label(nid: str) -> str:
    return nid.replace("C:concept::", "").replace("T:", "")

# -----------------------------
# DEBUG: PER-CORPUS TOP 80 TERMS (SIDE BY SIDE)
# -----------------------------

def debug_per_corpus_top_terms(g, corpora_ids, top_n=80):
    print("\n=== DEBUG: PER-CORPUS TOP 80 TERMS (SIDE BY SIDE) ===\n")

    # build per-corpus ranked word lists
    per_corpus = {}

    for corpus in corpora_ids:
        terms = []
        seen = set()

        for nid, node in g.nodes.items():
            support = getattr(node, "corpus_support", {}) or {}
            val = support.get(corpus, 0.0)
            if val <= 0:
                continue

            word = _label(nid)
            if word in seen:
                continue

            seen.add(word)
            terms.append((val, word))

        # rank internally by this corpus only
        terms.sort(key=lambda x: x[0], reverse=True)
        per_corpus[corpus] = [w for _, w in terms[:top_n]]

    # column header
    col_width = 14
    header = " #  " + "".join(f"{c[:col_width]:<{col_width}}" for c in corpora_ids)
    print(header)
    print("-" * len(header))

    # rows
    for i in range(top_n):
        row = f"{i+1:02d}  "
        for corpus in corpora_ids:
            words = per_corpus.get(corpus, [])
            cell = words[i] if i < len(words) else ""
            row += f"{cell:<{col_width}}"
        print(row)

# -----------------------------
# Main
# -----------------------------

def main():
    mode = "boot"
    args = sys.argv[1:]
    if "--tight" in args:
        mode = "tight"
        args.remove("--tight")

    q = " ".join(args).strip()
    if not q:
        print('Usage: python -m interpreter.interpreter_v1 [--tight] "your question"')
        sys.exit(1)

    P = TIGHT if mode == "tight" else BOOT
    seed_params = SeedParams(seed_min=P["seed_min"], seed_separation_distance=P["seed_sep"])
    cluster_params = ClusterParams(
        edge_min=P["edge_min"],
        merge_overlap=0.50,
        core_size=P["core_size"],
        max_growth_depth=2,
        more_clusters=True
    )
    spine_params = SpineParams(max_spines_shown=2, target_words=240, output_budget_mode="normal")
    m_current = MCurrent(strength=0.15)

    from interpreter.query_v2_adapter import QueryV2LiveAdapter
    adapter: QueryV2Adapter = QueryV2LiveAdapter()
    hits = adapter.run(q)

    by_corpus = defaultdict(list)
    for h in hits:
        by_corpus[h.corpus_id].append(h)

    essences = [build_semantic_essence_from_hits(cid, ch) for cid, ch in by_corpus.items()]

    g = InteractionGraph()
    for e in essences:
        add_essence_to_graph(g, e, edge_min=cluster_params.edge_min)

    add_cross_corpus_overlap_edges(g, edge_min=cluster_params.edge_min)

    print("\n[DEBUG] graph nodes =", len(g.nodes))
    print("[DEBUG] graph edges =", sum(len(v) for v in g.adj.values()) // 2)

    # >>> NEW DEBUG VIEW (THIS IS WHAT YOU ASKED FOR) <<<
    corpora_ids = sorted(by_corpus.keys())
    debug_per_corpus_top_terms(g, corpora_ids, top_n=80)

    # ---- normal interpreter continues unchanged ----
    seeds = select_seeds(g, seed_params, cluster_params)
    clusters = [grow_cluster_from_seed(g, sid, sc, f"C{i+1}", cluster_params)
                for i, (sid, sc) in enumerate(seeds)]
    clusters = merge_clusters(g, clusters, cluster_params)
    compute_bridges(g, clusters, cluster_params)

    q_terms = [t.lower() for t in q.split() if len(t) > 2]
    spines = build_spines(g, clusters, q_terms, m_current, spine_params)
    chosen = choose_spines_for_output(spines, spine_params)

    answer = (
        f"Across the analysed corpora, the dominant structure relates to {chosen[0].spine_type}."
        if chosen else
        "No stable semantic spine could be formed under current thresholds."
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"question": q, "answer": answer}, f, indent=2)

    print("\n=== ANSWER (v1 draft) ===")
    print(answer)

if __name__ == "__main__":
    main()
