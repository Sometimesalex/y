from __future__ import annotations
import sys
import json
from pathlib import Path
from typing import List
from collections import defaultdict

from interpreter.semantic_types import SeedParams, ClusterParams, SpineParams, MCurrent
from interpreter.graph import InteractionGraph
from interpreter.essence import QueryV2Adapter, QueryHit, build_semantic_essence_from_hits
from interpreter.builder import add_essence_to_graph, add_cross_corpus_overlap_edges
from interpreter.cluster import select_seeds, grow_cluster_from_seed, merge_clusters, compute_bridges
from interpreter.spines import build_spines, choose_spines_for_output
from interpreter.debug import cluster_card, spine_debug, ascii_cluster_adjacency

# -----------------------------
# Threshold modes
# -----------------------------

BOOT = dict(
    seed_min=1.0,
    seed_sep=1,
    edge_min=0.05,
    core_size=3,
)

TIGHT = dict(
    seed_min=3.0,
    seed_sep=2,
    edge_min=0.55,
    core_size=7,
)

# -----------------------------
# Paths
# -----------------------------

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "Interpreteroutput"
OUT_FILE = OUT_DIR / "interpreter_result.json"

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

    print(
        f"\n[MODE] {mode.upper()} | "
        f"seed_min={P['seed_min']} "
        f"edge_min={P['edge_min']} "
        f"core_size={P['core_size']}"
    )

    seed_params = SeedParams(
        seed_min=P["seed_min"],
        seed_separation_distance=P["seed_sep"]
    )

    cluster_params = ClusterParams(
        edge_min=P["edge_min"],
        merge_overlap=0.50,
        core_size=P["core_size"],
        max_growth_depth=2,
        more_clusters=True
    )

    spine_params = SpineParams(
        max_spines_shown=2,
        target_words=240,
        output_budget_mode="normal"
    )

    m_current = MCurrent(strength=0.15)

    # ---- real adapter ----
    from interpreter.query_v2_adapter import QueryV2LiveAdapter
    adapter: QueryV2Adapter = QueryV2LiveAdapter()

    hits = adapter.run(q)

    by_corpus = defaultdict(list)
    for h in hits:
        by_corpus[h.corpus_id].append(h)

    essences = []
    for corpus_id, chits in by_corpus.items():
        essences.append(build_semantic_essence_from_hits(corpus_id, chits))

    g = InteractionGraph()
    for e in essences:
        add_essence_to_graph(g, e, edge_min=cluster_params.edge_min)

    add_cross_corpus_overlap_edges(g, edge_min=cluster_params.edge_min)

    print("\n[DEBUG] graph nodes =", len(g.nodes))
    print("[DEBUG] graph edges =", sum(len(v) for v in g.adj.values()) // 2)
    print("[DEBUG] sample nodes =", list(g.nodes.keys())[:10])

    seeds = select_seeds(g, seed_params, cluster_params)

    clusters = []
    for idx, (seed_id, seed_sc) in enumerate(seeds):
        clusters.append(
            grow_cluster_from_seed(
                g, seed_id, seed_sc, f"C{idx+1}", cluster_params
            )
        )

    clusters = merge_clusters(g, clusters, cluster_params)
    compute_bridges(g, clusters, cluster_params)

    q_terms = [t.lower() for t in q.split() if len(t) > 2]

    spines = build_spines(g, clusters, q_terms, m_current, spine_params)
    chosen = choose_spines_for_output(spines, spine_params)

    # -----------------------------
    # Presentation extraction
    # -----------------------------

    answer_lines: List[str] = []
    context: List[str] = []

    if chosen:
        primary = chosen[0]

        # NOTE: spine_type is already a string (per your current output)
        answer_lines.append(
            "Across the analysed corpora, the dominant structure relates to "
            f"{primary.spine_type}."
        )

        # top concepts on the primary spine
        for nid in primary.nodes[:5]:
            label = nid.replace("C:concept::", "").replace("T:", "")
            answer_lines.append(f"- {label}")

        # FIX: SemanticEssence has no `.terms`; derive context from actual graph support
        seen = set()
        for nid in primary.nodes:
            node = g.nodes.get(nid)
            if not node:
                continue

            for corpus_id in getattr(node, "corpus_support", []):
                if corpus_id not in seen:
                    context.append(f"{corpus_id}")
                    seen.add(corpus_id)

            if len(context) >= 6:
                break

    else:
        answer_lines.append(
            "No stable semantic spine could be formed under current thresholds."
        )

    answer = "\n".join(answer_lines)

    # -----------------------------
    # Write interpreter output (FOR RENDERER)
    # -----------------------------

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "question": q,
        "answer": answer,
        "context": context,
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"\n[INTERPRETER] Wrote presentation output → {OUT_FILE}")

    # -----------------------------
    # Console output
    # -----------------------------

    print("\n=== ANSWER (v1 draft) ===")
    print(answer)

    print(
        "\nLimits: Given my current corpora and design constraints, "
        "I can relate these structures. If it feels incomplete, "
        "that reflects the limits of this interface in this moment, "
        "not a denial of relation."
    )

    print("\n=== DEBUG: CLUSTERS ===")
    for c in clusters:
        print(cluster_card(g, c))
        print()

    print("=== DEBUG: CLUSTER ADJACENCY ===")
    print(ascii_cluster_adjacency(g, clusters))
    print()

    print("=== DEBUG: SPINES ===")
    for s in spines:
        print(spine_debug(g, s))
        print()


if __name__ == "__main__":
    main()
