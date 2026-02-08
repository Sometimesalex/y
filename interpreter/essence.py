from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import re
from collections import Counter

from .semantic_types import SemanticEssence, WeightedTerm, ConceptNode, Motif, Tension, ToneSignature


@dataclass
class QueryHit:
    corpus_id: str
    doc_id: str
    text: str
    score: float


class QueryV2Adapter:
    """
    You implement this to return per-corpus hits from your query_v2.py.
    Keep it pure: question in, hits out.
    """
    def run(self, question: str) -> List[QueryHit]:
        raise NotImplementedError


def _simple_tokenize(s: str) -> List[str]:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s'-]", " ", s)
    toks = [t for t in s.split() if t and len(t) > 2]
    return toks


def build_semantic_essence_from_hits(corpus_id: str, hits: List[QueryHit], max_terms: int = 18) -> SemanticEssence:
    # v1: term repetition + crude concept mapping placeholder (you will replace with WordNet mappings)
    all_text = " ".join(h.text for h in hits)
    toks = _simple_tokenize(all_text)
    counts = Counter(toks)

    # dispersion proxy: count of distinct hit-docs where term appears / total docs
    doc_texts = [(h.doc_id, _simple_tokenize(h.text)) for h in hits]
    doc_has = Counter()
    for doc_id, dtoks in doc_texts:
        for t in set(dtoks):
            doc_has[t] += 1
    total_docs = max(1, len(doc_texts))

    key_terms: List[WeightedTerm] = []
    for term, cnt in counts.most_common(max_terms * 2):
        disp = doc_has.get(term, 0) / total_docs
        weight = float(cnt) * (0.5 + 0.5 * disp)  # repetition counted ONCE here
        key_terms.append(WeightedTerm(term=term, weight=weight, count=cnt, dispersion=disp))

    key_terms = sorted(key_terms, key=lambda x: x.weight, reverse=True)[:max_terms]

    # Placeholder concept extraction: treat top terms as concept labels
    key_concepts: List[ConceptNode] = []
    for wt in key_terms[: min(8, len(key_terms))]:
        cid = f"concept::{wt.term}"
        key_concepts.append(ConceptNode(concept_id=cid, label=wt.term, weight=wt.weight, aliases=(wt.term,)))

    # Motifs/tensions are left minimal in v1 until you add real pattern detection
    motifs: List[Motif] = []
    tensions: List[Tension] = []

    # Entropy: normalized type/token (rough)
    unique = len(counts)
    total = max(1, sum(counts.values()))
    entropy = min(1.0, unique / total * 6.0)

    # Tone signature (optional): crude posture detection
    posture = "mixed"
    if re.search(r"\b(must|should|ought)\b", all_text.lower()):
        posture = "prescriptive"
    elif re.search(r"\b(perhaps|maybe|seems)\b", all_text.lower()):
        posture = "exploratory"
    tone = ToneSignature(posture=posture, intensity="med")

    essence = SemanticEssence(
        corpus_id=corpus_id,
        key_terms=key_terms,
        key_concepts=key_concepts,
        motifs=motifs,
        tensions=tensions,
        entropy=entropy,
        tone=tone,
        provenance=[h.doc_id for h in hits],
    )
    return essence
