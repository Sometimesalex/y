from __future__ import annotations
from typing import List, Dict, Set

from .semantic_types import SemanticEssence, GraphNode, GraphEdge, NodeType, EdgeRel
from .graph import InteractionGraph
from .weights import REL_STRENGTH, evidence_factor, entropy_factor, cap_momentum

# -----------------------------
# Fix 2: stop-concept penalty
# -----------------------------

STOP_TERMS: Set[str] = {
    "and", "the", "his", "her", "that", "this", "with", "for",
    "not", "thou", "thy", "thee", "thine", "is", "are", "was",
}

STOP_PENALTY = 0.05  # keep structure, kill dominance


def add_essence_to_graph(g: InteractionGraph, essence: SemanticEssence, edge_min: float) -> None:
    g.entropy_by_corpus[essence.corpus_id] = essence.entropy

    # -----------------------------
    # TERM nodes
    # -----------------------------
    for wt in essence.key_terms:
        term = wt.term.lower()
        weight = wt.weight

        if term in STOP_TERMS:
            weight *= STOP_PENALTY

        g.ensure_node(GraphNode(
            node_id=f"T:{wt.term}",
            type=NodeType.TERM,
            weight=cap_momentum(weight),
            corpus_support={essence.corpus_id: weight},
            provenance=list(essence.provenance),
            payload_ref=f"{essence.corpus_id}:term:{wt.term}"
        ))

    # -----------------------------
    # CONCEPT nodes
    # -----------------------------
    concept_weight: Dict[str, float] = {}
    for c in essence.key_concepts:
        concept_weight[c.concept_id] = concept_weight.get(c.concept_id, 0.0) + c.weight

    for c in essence.key_concepts:
        concept = c.concept_id.lower()
        weight = concept_weight.get(c.concept_id, c.weight)

        if concept in STOP_TERMS:
            weight *= STOP_PENALTY

        g.ensure_node(GraphNode(
            node_id=f"C:{c.concept_id}",
            type=NodeType.CONCEPT,
            weight=cap_momentum(weight),
            corpus_support={essence.corpus_id: weight},
            provenance=list(essence.provenance),
            payload_ref=f"{essence.corpus_id}:concept:{c.concept_id}"
        ))

    # -----------------------------
    # Intra-corpus edges (UNCHANGED)
    # -----------------------------
    for wt in essence.key_terms[: min(10, len(essence.key_terms))]:
        t_id = f"T:{wt.term}"
        for c in essence.key_concepts[: min(6, len(essence.key_concepts))]:
            c_id = f"C:{c.concept_id}"

            rel = EdgeRel.SUPPORTS
            rs = REL_STRENGTH[rel]
            em = cap_momentum(min(wt.weight, c.weight))
            ef = evidence_factor(1)
            entf = entropy_factor(
                rel,
                essence.entropy,
                essence.entropy,
                cross_corpus_confirmed=False
            )

            w = rs * (em / 10.0) * ef * entf

            if w >= edge_min * 0.6:
                g.add_edge(GraphEdge(
                    src=t_id,
                    dst=c_id,
                    rel=rel,
                    weight=float(w),
                    evidence_corpora=[essence.corpus_id]
                ))
