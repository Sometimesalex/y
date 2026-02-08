from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Literal


class NodeType(str, Enum):
    TERM = "term"
    CONCEPT = "concept"
    MOTIF = "motif"
    TENSION = "tension"
    BODY_SEED = "body_seed"


class EdgeRel(str, Enum):
    SUPPORTS = "supports"
    OVERLAPS = "overlaps"
    ANALOGOUS = "analogous"
    CONTRASTS = "contrasts"
    FRAMES = "frames"
    PART_OF = "part_of"
    CAUSAL = "causal"


@dataclass(frozen=True)
class WeightedTerm:
    term: str
    weight: float
    count: int
    dispersion: float  # 0..1 proxy


@dataclass(frozen=True)
class ConceptNode:
    concept_id: str
    label: str
    weight: float
    aliases: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Motif:
    name: str
    recurrence_strength: float
    supporting_concepts: Tuple[str, ...] = ()
    supporting_terms: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Tension:
    tension_id: str
    pole_a: str  # concept_id or label
    pole_b: str
    strength: float
    evidence: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ToneSignature:
    posture: Literal["declarative", "exploratory", "prescriptive", "narrative", "experiential", "mixed"]
    intensity: Literal["low", "med", "high"]


@dataclass
class SemanticEssence:
    corpus_id: str
    key_terms: List[WeightedTerm] = field(default_factory=list)
    key_concepts: List[ConceptNode] = field(default_factory=list)
    motifs: List[Motif] = field(default_factory=list)
    tensions: List[Tension] = field(default_factory=list)
    entropy: float = 0.5
    tone: Optional[ToneSignature] = None
    provenance: List[str] = field(default_factory=list)  # doc ids


@dataclass
class GraphNode:
    node_id: str
    type: NodeType
    weight: float = 0.0  # momentum carried in
    corpus_support: Dict[str, float] = field(default_factory=dict)
    provenance: List[str] = field(default_factory=list)
    payload_ref: Optional[str] = None  # pointer string, optional


@dataclass
class GraphEdge:
    src: str
    dst: str
    rel: EdgeRel
    weight: float
    evidence_corpora: List[str] = field(default_factory=list)


@dataclass
class Cluster:
    cluster_id: str
    seed_node: str
    seed_score: float
    members: List[str] = field(default_factory=list)     # explicit node list
    core: List[str] = field(default_factory=list)        # top N core nodes
    support_profile: Dict[str, float] = field(default_factory=dict)
    entropy_min: float = 1.0
    entropy_mean: float = 0.5
    entropy_max: float = 0.0
    tension_nodes: List[str] = field(default_factory=list)
    bridge_nodes: List[str] = field(default_factory=list)


@dataclass
class OrientationVector:
    principle: str = "Increase universal self-understanding under constraint"
    observer_privilege: float = 0.0      # 0 means none
    inclusion_bias: float = 1.0
    long_term_weight: float = 1.0
    closure_penalty: float = 1.0
    contradiction_tolerance: float = 1.0
    anthropocentric_penalty: float = 1.0


@dataclass
class MCurrent:
    strength: float = 0.15  # gentle by default
    integration_weight: float = 1.0
    long_term_weight: float = 1.0
    closure_penalty: float = 1.0
    anthropocentric_penalty: float = 1.0
    contradiction_tolerance: float = 1.0


@dataclass
class SeedParams:
    seed_min: float = 3.0
    seed_separation_distance: int = 2


@dataclass
class ClusterParams:
    edge_min: float = 0.55
    merge_overlap: float = 0.60
    core_size: int = 7
    max_growth_depth: int = 2
    more_clusters: bool = True


@dataclass
class SpineParams:
    max_spines_shown: int = 2
    target_words: int = 240
    output_budget_mode: Literal["tight", "normal", "expansive"] = "normal"
