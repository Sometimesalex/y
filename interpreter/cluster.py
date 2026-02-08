from __future__ import annotations
from typing import Dict, List, Set, Tuple
from collections import defaultdict, deque
import statistics

from .types import (
    Cluster, NodeType, EdgeRel, SeedParams, ClusterParams, MCurrent
)
from .graph import InteractionGraph


SEED_ALLOWED_TYPES = {NodeType.CONCEPT, NodeType.MOTIF, NodeType.TENSION}
DEGREE_ALLOWED_RELS = {EdgeRel.SUPPORTS, EdgeRel.ANALOGOUS, EdgeRel.CONTRASTS, EdgeRel.FRAMES, EdgeRel.PART_OF, EdgeRel.OVERLAPS}
DEGREE_ALLOWED_NEIGHBORS = {NodeType.CONCEPT, NodeType.MOTIF, NodeType.TENSION}


def seed_score(g: InteractionGraph, node_id: str, params: ClusterParams) -> float:
    n = g.nodes[node_id]
    support_count = sum(1 for _, v in n.corpus_support.items() if v > 0)
    A = 0.0 if support_count <= 1 else min(4.0, float(support_count))  # 2->2, 3->3, 4+->4 approx
    if support_count == 2:
        A = 2.0
    elif support_count == 3:
        A = 3.0
    elif support_count >= 4:
        A = 4.0

    deg = g.degree_strong(node_id, params.edge_min, DEGREE_ALLOWED_RELS, DEGREE_ALLOWED_NEIGHBORS)
    B = min(3.0, deg / 3.0)

    # C) tension richness bonus (v1 placeholder; full pole support needs real tension structure)
    C = 0.0
    if n.type == NodeType.TENSION:
        C = 1.0

    # D) entropy balance: supported by both hot and cold corpora
    ent_sources = []
    for cid in n.corpus_support.keys():
        if cid in g.entropy_by_corpus:
            ent_sources.append(g.entropy_by_corpus[cid])
    D = 0.0
    if ent_sources:
        if any(e < 0.45 for e in ent_sources) and any(e >= 0.70 for e in ent_sources):
            D = 1.0

    return A + B + C + D


def select_seeds(g: InteractionGraph, seed_params: SeedParams, cluster_params: ClusterParams) -> List[Tuple[str, float]]:
    candidates = [nid for nid in g.nodes if g.nodes[nid].type in SEED_ALLOWED_TYPES]
    scored = [(nid, seed_score(g, nid, cluster_params)) for nid in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    seeds: List[Tuple[str, float]] = []
    for nid, sc in scored:
        if sc < seed_params.seed_min:
            continue
        # separation: skip if too close to an existing seed via strong edges
        if _too_close_to_existing_seed(g, nid, seeds, seed_params.seed_separation_distance, cluster_params.edge_min):
            continue
        seeds.append((nid, sc))
    return seeds


def _too_close_to_existing_seed(g: InteractionGraph, nid: str, seeds: List[Tuple[str, float]], dist: int, edge_min: float) -> bool:
    if not seeds:
        return False
    targets = {s for s, _ in seeds}
    # BFS limited depth along strong edges (core types only)
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


def grow_cluster_from_seed(g: InteractionGraph, seed: str, seed_sc: float, cluster_id: str, params: ClusterParams) -> Cluster:
    # BFS growth with depth, core types only; attach terms later as satellites if desired
    members: Set[str] = set([seed])
    frontier = deque([(seed, 0)])
    while frontier:
        cur, depth = frontier.popleft()
        if depth >= params.max_growth_depth:
            continue
        for e in g.neighbors(cur):
            if e.weight < params.edge_min:
                continue
            nt = g.node_type(e.dst)
            if nt not in {NodeType.CONCEPT, NodeType.MOTIF, NodeType.TENSION, NodeType.TERM}:
                continue
            if e.dst not in members:
                members.add(e.dst)
                frontier.append((e.dst, depth + 1))

    cluster = Cluster(cluster_id=cluster_id, seed_node=seed, seed_score=seed_sc, members=sorted(members))
    _compute_cluster_profiles(g, cluster, params)
    return cluster


def _compute_cluster_profiles(g: InteractionGraph, cluster: Cluster, params: ClusterParams) -> None:
    # support profile
    support = defaultdict(float)
    entropies = []
    tensions = []
    for nid in cluster.members:
        n = g.nodes[nid]
        for cid, v in n.corpus_support.items():
            support[cid] += v
        # entropy per node from its supporting corpora
        for cid in n.corpus_support.keys():
            if cid in g.entropy_by_corpus:
                entropies.append(g.entropy_by_corpus[cid])
        if n.type == NodeType.TENSION:
            tensions.append(nid)

    cluster.support_profile = dict(support)
    if entropies:
        cluster.entropy_min = min(entropies)
        cluster.entropy_max = max(entropies)
        cluster.entropy_mean = float(statistics.mean(entropies))
    cluster.tension_nodes = tensions

    # core nodes = top momentum among concept/motif/tension
    core_candidates = [nid for nid in cluster.members if g.nodes[nid].type in {NodeType.CONCEPT, NodeType.MOTIF, NodeType.TENSION}]
    core_candidates.sort(key=lambda nid: g.nodes[nid].weight, reverse=True)
    cluster.core = core_candidates[: params.core_size]


def compute_bridges(g: InteractionGraph, clusters: List[Cluster], params: ClusterParams) -> None:
    # B1 shared core membership
    core_to_clusters = defaultdict(list)
    for c in clusters:
        for nid in c.core:
            core_to_clusters[nid].append(c.cluster_id)

    cluster_by_id = {c.cluster_id: c for c in clusters}

    # Shared membership bridges
    for nid, cids in core_to_clusters.items():
        if len(cids) >= 2:
            for cid in cids:
                cluster_by_id[cid].bridge_nodes.append(nid)

    # B2 strong cross-cluster connectivity bridges
    # For each cluster core node, see strong edges to another cluster's core nodes
    core_set_by_cluster = {c.cluster_id: set(c.core) for c in clusters}
    for c in clusters:
        for nid in c.core:
            hits = defaultdict(int)  # other_cluster -> count
            for e in g.neighbors(nid):
                if e.weight < params.edge_min:
                    continue
                dst = e.dst
                # find which cluster cores contain dst
                for other in clusters:
                    if other.cluster_id == c.cluster_id:
                        continue
                    if dst in core_set_by_cluster[other.cluster_id]:
                        hits[other.cluster_id] += 1
            for other_id, cnt in hits.items():
                if cnt >= 2:
                    c.bridge_nodes.append(nid)
                    cluster_by_id[other_id].bridge_nodes.append(nid)


def should_merge(g: InteractionGraph, a: Cluster, b: Cluster, params: ClusterParams) -> bool:
    core_a = set(a.core)
    core_b = set(b.core)
    if not core_a or not core_b:
        return False
    overlap = len(core_a & core_b) / float(min(len(core_a), len(core_b)))
    if overlap < params.merge_overlap:
        return False

    # dominance similarity: compare top corpus share
    def top_share(c: Cluster) -> float:
        total = sum(c.support_profile.values()) or 1.0
        top = max(c.support_profile.values()) if c.support_profile else 0.0
        return top / total

    # if one is heavily dominated and the other isn't similarly shaped, avoid merge
    if abs(top_share(a) - top_share(b)) > 0.35:
        return False

    # tensions: don't merge if they are connected mainly by bridges (handled later); for now keep strict
    return True


def merge_clusters(g: InteractionGraph, clusters: List[Cluster], params: ClusterParams) -> List[Cluster]:
    # conservative merging: try pairs, merge if should_merge; repeat until stable
    merged = True
    cluster_list = clusters[:]
    i = 0
    while merged:
        merged = False
        out: List[Cluster] = []
        used = set()
        for i in range(len(cluster_list)):
            if i in used:
                continue
            ci = cluster_list[i]
            did_merge = False
            for j in range(i + 1, len(cluster_list)):
                if j in used:
                    continue
                cj = cluster_list[j]
                if should_merge(g, ci, cj, params):
                    new_members = sorted(set(ci.members) | set(cj.members))
                    new_id = f"{ci.cluster_id}+{cj.cluster_id}"
                    new_cluster = Cluster(cluster_id=new_id, seed_node=ci.seed_node, seed_score=max(ci.seed_score, cj.seed_score), members=new_members)
                    _compute_cluster_profiles(g, new_cluster, params)
                    out.append(new_cluster)
                    used.add(i)
                    used.add(j)
                    merged = True
                    did_merge = True
                    break
            if not did_merge and i not in used:
                out.append(ci)
                used.add(i)
        cluster_list = out
    return cluster_list
