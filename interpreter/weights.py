from __future__ import annotations
from typing import Dict
from .semantic_types import EdgeRel, NodeType


REL_STRENGTH: Dict[EdgeRel, float] = {
    EdgeRel.SUPPORTS: 1.0,
    EdgeRel.OVERLAPS: 0.9,
    EdgeRel.ANALOGOUS: 0.7,
    EdgeRel.CONTRASTS: 0.7,
    EdgeRel.FRAMES: 0.6,
    EdgeRel.PART_OF: 0.6,
    EdgeRel.CAUSAL: 0.5,
}


def evidence_factor(corpus_count: int) -> float:
    if corpus_count <= 1:
        return 1.0
    if corpus_count == 2:
        return 1.2
    if corpus_count == 3:
        return 1.35
    return 1.45


def entropy_factor(edge_rel: EdgeRel, entropy_src: float, entropy_dst: float, cross_corpus_confirmed: bool) -> float:
    # entropy is semantic temperature; we allow exploration but down-weight soft analogies unless confirmed
    hot = (entropy_src + entropy_dst) / 2.0
    if edge_rel == EdgeRel.ANALOGOUS and hot >= 0.7 and not cross_corpus_confirmed:
        return 0.85
    return 1.0


def cap_momentum(m: float, cap: float = 10.0) -> float:
    return min(m, cap)
