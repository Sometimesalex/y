from __future__ import annotations
import sys
from typing import List, Dict
from collections import defaultdict

from interpreter.semantic_types import SeedParams, ClusterParams, SpineParams, MCurrent
from interpreter.graph import InteractionGraph
from interpreter.essence import QueryV2Adapter, QueryHit, build_semantic_essence_from_hits
from interpreter.builder import add_essence_to_graph, add_cross_corpus_overlap_edges
from interpreter.cluster import select_seeds, grow_cluster_from_seed, merge_clusters, compute_bridges
from interpreter.spines import build_spines, choose_spines_for_output
from interpreter.debug import cluster_card, spine_debug, ascii_cluster_adjacency


class DummyAdapter(QueryV2Adapter):
    # Replace this with a real adapter calling query_v2.py
    def run(self, question: str) -> List[QueryHit]:
        # minimal dummy: pretend there are two corpora
        return [
            QueryHit(corpus_id="corpus_a", doc_id="a1", text=f"{question} relates to meaning, identity, evolution, constraint.", score=0.9),
            QueryHit(corpus_id="corpus_b", doc_id="b1", text=f"{question} relates to tension, contradiction, order and chaos.", score=0.8),
        ]


def main():
    q = " ".join(sys.argv[1:]).strip()
    if not q:
        print("Usage: python scripts/interpreter_v1.py \"your question\"")
        sys.exit(1)

    # params (v1 more clusters)
    seed_params = SeedParams(seed_min=1.0, seed_separation_distance=1)
    cluster_params = ClusterParams(edge_min=0.05, merge_overlap=0.50, core_size=3, max_growth_depth=2, more_clusters=True)
    spine_params = SpineParams(max_spines_shown=2, target_words=240, output_budget_mode="normal")
    m_current = MCurrent(strength=0.15)

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
        clusters.append(grow_cluster_from_seed(g, seed_id, seed_sc, f"C{idx+1}", cluster_params))

    clusters = merge_clusters(g, clusters, cluster_params)
    compute_bridges(g, clusters, cluster_params)

    # Very crude question term extraction (replace with your tokenizer)
    q_terms = [t.lower() for t in q.split() if len(t) > 2]

    spines = build_spines(g, clusters, q_terms, m_current, spine_params)
    chosen = choose_spines_for_output(spines, spine_params)

    # Answer (v1 minimal — you will upgrade)
    print("\n=== ANSWER (v1 draft) ===")
    if chosen:
        primary = chosen[0]
        print(f"Primary spine ({primary.spine_type}):")
        for nid in primary.nodes[:10]:
            n = g.nodes[nid]
            print(f"- {nid} [{n.type.value}] (w={n.weight:.2f}, corpora={len(n.corpus_support)})")
        if len(chosen) > 1:
            sec = chosen[1]
            print(f"\nSecondary spine ({sec.spine_type}):")
            for nid in sec.nodes[:8]:
                n = g.nodes[nid]
                print(f"- {nid} [{n.type.value}]")
    else:
        print("No spines produced (insufficient graph connectivity).")

    print("\nLimits: Given my current corpora and design constraints, I can relate these structures. If it feels incomplete, that reflects the limits of this interface in this moment, not a denial of relation.")

    # Debug
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
