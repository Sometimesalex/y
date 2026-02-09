from __future__ import annotations
from typing import Dict, List, Set, Tuple
from collections import defaultdict, deque
import statistics

from .semantic_types import (
    Cluster, NodeType, EdgeRel, SeedParams, ClusterParams, MCurrent
)
from .graph import InteractionGraph


SEED_ALLOWED_TYPES = {NodeType.CONCEPT, NodeType.MOTIF, NodeType.TENSION}
DEGREE_ALLOWED_RELS = {
    EdgeRel.SUPPORTS,
    EdgeRel.ANALOGOUS,
    EdgeRel.CONTRASTS,
    EdgeRel.FRAMES,
    EdgeRel.PART_OF,
    EdgeRel.OVERLAPS,
}
DEGREE_ALLOWED_NEIGHBORS = {
    NodeType.CONCEPT,
    NodeType.MOTIF,
    NodeType.TENSION,
}

# -------------------------------------------------
# FIX 2: stop high-frequency glue concepts from seeding
# -------------------------------------------------

STOP_SEED_TERMS = {
    "and", "the", "his", "her", "their", "that", "this",
    "with", "not", "for", "from", "was", "were", "are",
    "is", "of", "to", "in", "on", "by", "as"
}


def seed_score(g: InteractionGraph, node_id: str, params: ClusterParams) -> float:
    n = g.nodes[node_id]
    support_count = sum(1 for _, v in n.corpus_support.items() if v > 0)

    # A) cross-corpus support
    if support_count <= 1:
        A = 0.0
    elif support_count == 2:
        A = 2.0
    elif support_count == 3:
        A = 3.0
    else:
        A = 4.0

    # B) structural connectivity
    deg = g.degree_strong(
        node_id,
        params.edge_min,
        DEGREE_ALLOWED_RELS,
        DEGREE_ALLOWED_NEIGHBORS
    )
    B = min(3.0, deg / 3.0)

    # C) tension richness
    C = 1.0 if n.type == NodeType.TENSION else 0.0

    # D) entropy balance
    ent_sources = [
        g.entropy_by_corpus[cid]
        for cid in n.corpus_support.keys()
        if cid in g.entropy_by_corpus
    ]
    D = 0.0
    if ent_sources:
        if any(e < 0.45 for e in ent_sources) and any(e >= 0.70 for e in ent_sources):
            D = 1.0

    return A + B + C + D


def select_seeds(
    g: InteractionGraph,
    seed_params: SeedParams,
    cluster_params: ClusterParams
) -> List[Tuple[str, float]]:

    candidates: List[str] = []

    for nid, node in g.nodes.items():
        if node.type not in SEED_ALLOWED_TYPES:
            continue

        # -------------------------------------------------
        # FIX 2: block glue concepts from becoming seeds
        # -------------------------------------------------
        if node.type == NodeType.CONCEPT:
            term = nid.replace("C:concept::", "")
            if term in STOP_SEED_TERMS:
                continue

        candidates.append(nid)

    scored = [(nid, seed_score(g, nid, cluster_params)) for nid in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    seeds: List[Tuple[str, float]] = []
    for nid, sc in scored:
        if sc < seed_params.seed_min:
            continue

        # separation constraint
        if _too_close_to_existing_seed(
            g,
            nid,
            seeds,
            seed_params.seed_separation_distance,
            cluster_params.edge_min
        ):
            continue

        seeds.append((nid, sc))

    return seeds


def _too_close_to_existing_seed(
    g: InteractionGraph,
    nid: str,
    seeds: List[Tuple[str, float]],
    dist: int,
    edge_min: float
) -> bool:
    if not seeds:
        return False

    targets = {s for s, _ in seeds}
    q = deque([(nid, 0)])
    seen = {nid}

    while q:
        cur, d = q.popleft()
        if d > dist:
            continue
        if cur in targets and cur != nid:
            return True
        if d == dist:
            continue

        for e in g.neighbors(cur):
            if e.weight < edge_min:
                continue
            nt = g.node_type(e.dst)
            if nt not in SEED_ALLOWED_TYPES:
                continue
            if e.dst not in seen:
                seen.add(e.dst)
                q.append((e.dst, d + 1))

    return False
