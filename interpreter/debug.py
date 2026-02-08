from __future__ import annotations
from typing import List, Dict
from .semantic_types import Cluster
from .graph import InteractionGraph
from .spines import Spine


def cluster_card(g: InteractionGraph, c: Cluster) -> str:
    top_nodes = c.core[:5]
    def fmt(nid: str) -> str:
        n = g.nodes[nid]
        sup = len(n.corpus_support)
        return f"{nid}({n.type.value},w={n.weight:.2f},sup={sup})"

    lines = []
    lines.append(f"=== Cluster {c.cluster_id} ===")
    lines.append(f"Seed: {c.seed_node}  SeedScore: {c.seed_score:.2f}")
    lines.append(f"Members: {len(c.members)}  Core: {len(c.core)}  Bridges: {len(set(c.bridge_nodes))}")
    lines.append(f"Entropy min/mean/max: {c.entropy_min:.2f}/{c.entropy_mean:.2f}/{c.entropy_max:.2f}")
    lines.append("Support profile (top 5):")
    sp = sorted(c.support_profile.items(), key=lambda kv: kv[1], reverse=True)[:5]
    lines.append("  " + ", ".join([f"{k}:{v:.1f}" for k, v in sp]) if sp else "  (none)")
    lines.append("Top core nodes:")
    lines.append("  " + "  ".join(fmt(n) for n in top_nodes) if top_nodes else "  (none)")
    if c.tension_nodes:
        lines.append("Tension nodes:")
        lines.append("  " + "  ".join(c.tension_nodes[:5]))
    if c.bridge_nodes:
        lines.append("Bridge nodes (sample):")
        lines.append("  " + "  ".join(list(dict.fromkeys(c.bridge_nodes))[:6]))
    return "\n".join(lines)


def spine_debug(g: InteractionGraph, s: Spine) -> str:
    lines = []
    lines.append(f"--- Spine: {s.spine_type} --- score={s.score:.2f}")
    lines.append("Breakdown: " + ", ".join([f"{k}={v:.2f}" for k, v in s.score_breakdown.items()]))
    lines.append("Clusters: " + " -> ".join(s.clusters))
    lines.append("Nodes:")
    for nid in s.nodes[:20]:
        n = g.nodes.get(nid)
        if not n:
            continue
        lines.append(f"  {nid}  ({n.type.value})  w={n.weight:.2f}  corpora={len(n.corpus_support)}")
    if len(s.nodes) > 20:
        lines.append(f"  ... +{len(s.nodes)-20} more")
    return "\n".join(lines)


def ascii_cluster_adjacency(g: InteractionGraph, clusters: List[Cluster]) -> str:
    # show bridges as adjacency hints
    core_sets = {c.cluster_id: set(c.core) for c in clusters}
    lines = []
    for i in range(len(clusters)):
        for j in range(i + 1, len(clusters)):
            a, b = clusters[i], clusters[j]
            shared = list(core_sets[a.cluster_id] & core_sets[b.cluster_id])
            if shared:
                n = shared[0]
                lines.append(f"{a.cluster_id} --(shared: {n})--> {b.cluster_id}")
                continue
            # else check for a bridge node present in both bridge lists
            bridge = set(a.bridge_nodes) & set(b.bridge_nodes)
            if bridge:
                n = list(bridge)[0]
                lines.append(f"{a.cluster_id} --(bridge: {n})--> {b.cluster_id}")
    return "\n".join(lines) if lines else "(no visible adjacencies)"
