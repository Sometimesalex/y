from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set
import math

from .semantic_types import NodeType, Cluster, SpineParams, MCurrent
from .graph import InteractionGraph


# -----------------------------
# Glue penalty configuration
# -----------------------------

GLUE_TERMS = {
    "and", "or", "the", "a", "an", "of", "to", "in", "is", "was", "were",
    "be", "been", "being", "that", "this", "these", "those",
    "his", "her", "their", "its", "with", "for", "on", "by", "as", "at",
    "from", "not", "but", "which", "who", "whom", "what"
}

GLUE_PENALTY = 0.25  # keep structure, reduce dominance


def _label(nid: str) -> str:
    return nid.replace("C:concept::", "").replace("T:", "").lower()


def _adjusted_weight(g: InteractionGraph, nid: str) -> float:
    n = g.nodes[nid]
    if _label(nid) in GLUE_TERMS:
        return n.weight * GLUE_PENALTY
    return n.weight


@dataclass
class Spine:
    spine_type: str  # "invariant" | "tension" | "delta"
    nodes: List[str]
    clusters: List[str]
    score: float
    score_breakdown: Dict[str, float]


def _question_region(g: InteractionGraph, question_terms: List[str]) -> Set[str]:
    qnodes = set()
    for t in question_terms:
        tid = f"T:{t}"
        if tid in g.nodes:
            qnodes.add(tid)

    # also include linked concepts
    for nid in list(qnodes):
        for e in g.neighbors(nid):
            if g.node_type(e.dst) == NodeType.CONCEPT:
                qnodes.add(e.dst)

    return qnodes


def build_spines(
    g: InteractionGraph,
    clusters: List[Cluster],
    question_terms: List[str],
    m: MCurrent,
    params: SpineParams
) -> List[Spine]:

    qreg = _question_region(g, question_terms)

    cluster_hits = [c for c in clusters if set(c.members) & qreg]

    if not cluster_hits:
        cluster_hits = sorted(
            clusters,
            key=lambda c: sum(c.support_profile.values()),
            reverse=True
        )[:3]

    inv = _spine_invariant(g, cluster_hits, qreg, m)
    ten = _spine_tension(g, cluster_hits, qreg, m)
    delt = _spine_delta(g, clusters, cluster_hits, qreg, m)

    spines = [inv, ten, delt]
    spines.sort(key=lambda s: s.score, reverse=True)
    return spines


def _cluster_foreground_bonus(c: Cluster, m: MCurrent) -> float:
    total = sum(c.support_profile.values()) or 1.0
    top = max(c.support_profile.values()) if c.support_profile else 0.0
    dominance = top / total
    diversity = 1.0 - dominance
    return m.strength * (0.6 * diversity + 0.4 * (1.0 - dominance))


def _spine_invariant(
    g: InteractionGraph,
    cluster_hits: List[Cluster],
    qreg: Set[str],
    m: MCurrent
) -> Spine:

    nodes = []
    clusters_used = []
    inv_score = 0.0
    qfit = 0.0
    mcur = 0.0

    for c in cluster_hits[:2]:
        clusters_used.append(c.cluster_id)
        mcur += _cluster_foreground_bonus(c, m)

        core = [
            nid for nid in c.core
            if g.nodes[nid].type in {NodeType.CONCEPT, NodeType.MOTIF}
        ]

        core.sort(
            key=lambda nid: (
                len(g.nodes[nid].corpus_support),
                _adjusted_weight(g, nid)
            ),
            reverse=True
        )

        pick = core[:6]
        nodes.extend(pick)

        qfit += len(set(pick) & qreg) * 0.5

        inv_score += sum(
            min(4, len(g.nodes[nid].corpus_support))
            * _adjusted_weight(g, nid)
            for nid in pick
        ) * 0.6

    score = 1.4 * qfit + 1.2 * inv_score + mcur

    return Spine(
        "invariant",
        _dedupe(nodes),
        clusters_used,
        score,
        {
            "QFit": qfit,
            "Invariant": inv_score,
            "MCurrent": mcur,
            "ClosureRisk": 0.0
        }
    )


def _spine_tension(
    g: InteractionGraph,
    cluster_hits: List[Cluster],
    qreg: Set[str],
    m: MCurrent
) -> Spine:

    nodes = []
    clusters_used = []
    qfit = 0.0
    ten_score = 0.0
    mcur = 0.0

    for c in cluster_hits[:2]:
        clusters_used.append(c.cluster_id)
        mcur += _cluster_foreground_bonus(c, m)

        tens = [nid for nid in c.tension_nodes if nid in c.members]
        tens.sort(key=lambda nid: _adjusted_weight(g, nid), reverse=True)

        pick = tens[:4]
        nodes.extend(pick)

        for t in pick:
            for e in g.neighbors(t):
                if g.node_type(e.dst) == NodeType.CONCEPT and e.weight >= 0.55:
                    nodes.append(e.dst)

        qfit += len(set(nodes) & qreg) * 0.35
        ten_score += len(pick)

    score = 1.1 * qfit + 1.6 * ten_score + mcur

    return Spine(
        "tension",
        _dedupe(nodes),
        clusters_used,
        score,
        {
            "QFit": qfit,
            "Tension": ten_score,
            "MCurrent": mcur,
            "ClosureRisk": 0.0
        }
    )


def _spine_delta(
    g: InteractionGraph,
    all_clusters: List[Cluster],
    cluster_hits: List[Cluster],
    qreg: Set[str],
    m: MCurrent
) -> Spine:

    if not all_clusters:
        return Spine("delta", [], [], 0.0, {})

    nodes = []
    clusters_used = []
    qfit = 0.0
    mcur = 0.0

    primary = cluster_hits[0] if cluster_hits else all_clusters[0]

    def dominance(c: Cluster) -> float:
        total = sum(c.support_profile.values()) or 1.0
        top = max(c.support_profile.values()) if c.support_profile else 0.0
        return top / total

    target = max(
        (c for c in all_clusters if c.cluster_id != primary.cluster_id),
        key=lambda c: abs(dominance(c) - dominance(primary)),
        default=primary
    )

    best = abs(dominance(target) - dominance(primary))

    for c in [primary, target]:
        clusters_used.append(c.cluster_id)
        mcur += _cluster_foreground_bonus(c, m)

        core = [
            nid for nid in c.core
            if g.nodes[nid].type in {NodeType.CONCEPT, NodeType.MOTIF, NodeType.TENSION}
        ]

        core.sort(key=lambda nid: _adjusted_weight(g, nid), reverse=True)
        nodes.extend(core[:6])

        qfit += len(set(core) & qreg) * 0.3

    score = 1.0 * qfit + 1.3 * (best * 3.0) + mcur

    return Spine(
        "delta",
        _dedupe(nodes),
        clusters_used,
        score,
        {
            "QFit": qfit,
            "Delta": best * 3.0,
            "MCurrent": mcur,
            "ClosureRisk": 0.0
        }
    )


def _dedupe(xs: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def choose_spines_for_output(spines: List[Spine], params: SpineParams) -> List[Spine]:
    if not spines:
        return []

    primary = spines[0]
    secondary = None

    for s in spines[1:]:
        if s.spine_type != primary.spine_type:
            secondary = s
            break

    chosen = [primary]
    if secondary and params.max_spines_shown >= 2:
        chosen.append(secondary)

    return chosen
