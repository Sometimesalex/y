from __future__ import annotations
from typing import List, Dict, Set

from .types import SemanticEssence, GraphNode, GraphEdge, NodeType, EdgeRel
from .graph import InteractionGraph
from .weights import REL_STRENGTH, evidence_factor, entropy_factor, cap_momentum


def add_essence_to_graph(g: InteractionGraph, essence: SemanticEssence, edge_min: float) -> None:
    g.entropy_by_corpus[essence.corpus_id] = essence.entropy

    # Term nodes
    for wt in essence.key_terms:
        nid = f"T:{wt.term}"
        g.ensure_node(GraphNode(
            node_id=nid,
            type=NodeType.TERM,
            weight=cap_momentum(wt.weight),
            corpus_support={essence.corpus_id: wt.weight},
            provenance=list(essence.provenance),
            payload_ref=f"{essence.corpus_id}:term:{wt.term}"
        ))

    # Concept nodes (momentum inherited from terms; no re-counting repetition)
    concept_weight: Dict[str, float] = {}
    for c in essence.key_concepts:
        concept_weight[c.concept_id] = concept_weight.get(c.concept_id, 0.0) + c.weight

    for c in essence.key_concepts:
        nid = f"C:{c.concept_id}"
        g.ensure_node(GraphNode(
            node_id=nid,
            type=NodeType.CONCEPT,
            weight=cap_momentum(concept_weight.get(c.concept_id, c.weight)),
            corpus_support={essence.corpus_id: concept_weight.get(c.concept_id, c.weight)},
            provenance=list(essence.provenance),
            payload_ref=f"{essence.corpus_id}:concept:{c.concept_id}"
        ))

    # Intra-corpus edges: term -> concept supports
    # v1: link top terms to top concepts (you'll replace with real mapping)
    for wt in essence.key_terms[: min(10, len(essence.key_terms))]:
        t_id = f"T:{wt.term}"
        for c in essence.key_concepts[: min(6, len(essence.key_concepts))]:
            c_id = f"C:{c.concept_id}"

            # compute a conservative weight
            rel = EdgeRel.SUPPORTS
            rs = REL_STRENGTH[rel]
            em = cap_momentum(min(wt.weight, c.weight))
            ef = evidence_factor(1)
            entf = entropy_factor(rel, essence.entropy, essence.entropy, cross_corpus_confirmed=False)
            w = rs * (em / 10.0) * ef * entf  # normalize a bit

            if w >= edge_min * 0.6:  # allow local skeleton to exist a bit below edge_min
                g.add_edge(GraphEdge(src=t_id, dst=c_id, rel=rel, weight=float(w), evidence_corpora=[essence.corpus_id]))


def add_cross_corpus_overlap_edges(g: InteractionGraph, edge_min: float) -> None:
    # Create overlaps between identical TERM nodes across corpora implicitly via shared node support.
    # Create overlaps between CONCEPT nodes that share the same concept_id (already shared node_id).
    # v1: no extra edges required; shared nodes already unify.
    pass
