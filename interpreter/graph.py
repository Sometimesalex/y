from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Iterable, Optional, Set, Tuple

from .semantic_types import GraphNode, GraphEdge, NodeType, EdgeRel


@dataclass
class InteractionGraph:
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    adj: Dict[str, List[GraphEdge]] = field(default_factory=dict)
    entropy_by_corpus: Dict[str, float] = field(default_factory=dict)

    def ensure_node(self, node: GraphNode) -> None:
        if node.node_id not in self.nodes:
            self.nodes[node.node_id] = node
            self.adj[node.node_id] = []
        else:
            # merge support + weight (momentum adds, but cap elsewhere if needed)
            existing = self.nodes[node.node_id]
            existing.weight += node.weight
            for k, v in node.corpus_support.items():
                existing.corpus_support[k] = existing.corpus_support.get(k, 0.0) + v
            existing.provenance.extend(node.provenance)

    def add_edge(self, edge: GraphEdge) -> None:
        # undirected for clustering simplicity (store both directions)
        self.adj[edge.src].append(edge)
        self.adj[edge.dst].append(GraphEdge(
            src=edge.dst, dst=edge.src, rel=edge.rel, weight=edge.weight, evidence_corpora=edge.evidence_corpora
        ))

    def neighbors(self, node_id: str) -> List[GraphEdge]:
        return self.adj.get(node_id, [])

    def node_type(self, node_id: str) -> Optional[NodeType]:
        n = self.nodes.get(node_id)
        return n.type if n else None

    def nodes_of_types(self, allowed: Set[NodeType]) -> List[str]:
        return [nid for nid, n in self.nodes.items() if n.type in allowed]

    def degree_strong(self, node_id: str, edge_min: float,
                      allowed_rels: Set[EdgeRel],
                      allowed_neighbor_types: Set[NodeType]) -> int:
        c = 0
        for e in self.neighbors(node_id):
            if e.weight < edge_min:
                continue
            if e.rel not in allowed_rels:
                continue
            nt = self.node_type(e.dst)
            if nt is None or nt not in allowed_neighbor_types:
                continue
            c += 1
        return c
