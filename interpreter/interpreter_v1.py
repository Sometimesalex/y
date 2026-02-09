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

# -----------------------------
# DEBUG: GLOBAL TOP N
# -----------------------------

def debug_top_weighted_nodes(g, n=80):
    items = list(g.nodes.items())
    ranked = sorted(items, key=lambda kv: getattr(kv[1], "weight", 0.0), reverse=True)

    print(f"\n=== DEBUG: TOP {n} PROMOTED TERMS BY WEIGHT ===")
    for i, (nid, node) in enumerate(ranked[:n], 1):
        label = nid.replace("C:concept::", "").replace("T:", "")
        corpora = len(getattr(node, "corpus_support", {}) or {})
        print(f"{i:02d}. {label:<18} w={node.weight:7.2f} corpora={corpora}")

    return ranked[:n]

# -----------------------------
# DEBUG: COMPARATIVE MATRIX
# -----------------------------

def debug_corpus_comparison_matrix(top_nodes, corpora_ids, width=8):
    print("\n=== DEBUG: TOP 80 TERMS — CORPUS COMPARISON MATRIX ===")

    header = f"{'TERM':<18} " + " ".join(f"{c[:width]:>{width}}" for c in corpora_ids)
    print(header)
    print("-" * len(header))

    for nid, node in top_nodes:
        label = nid.replace("C:concept::", "").replace("T:", "")
        row = f"{label:<18} "
        support = getattr(node, "corpus_support", {}) or {}

        for c in corpora_ids:
            val = support.get(c, 0.0)
            row += f"{val:>{width}.2f}"

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
    cluster_params = ClusterParams(edge_min=P["edge_min"], merge_overlap=0.50,
                                   core_size=P["core_size"], max_growth_depth=2,
                                   more_clusters=True)
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

    # ---- GLOBAL TOP 80 ----
    top_nodes = debug_top_weighted_nodes(g, 80)

    # ---- CORPUS MATRIX ----
    corpora_ids = sorted(by_corpus.keys())
    debug_corpus_comparison_matrix(top_nodes, corpora_ids)

    # ---- NORMAL PIPELINE CONTINUES ----
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
