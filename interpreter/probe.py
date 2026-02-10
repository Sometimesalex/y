"""
probe.py — Semantic Probe Layer

Purpose:
- Use GCIDE as a *hypothesis generator*, not a source of truth.
- Extract trait-like tokens from dictionary definitions.
- Feed those traits into interpreter_v2 as query expansion hints.

GCIDE RULE:
- GCIDE suggests traits
- Corpora decide meaning
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Set, Iterable, Optional


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z'\-]*")


def norm(s: str) -> str:
    return (s or "").lower().strip()


def tokenize(text: str) -> List[str]:
    return [norm(m.group(0)) for m in TOKEN_RE.finditer(text or "")]


@dataclass
class ProbeResult:
    definitions: Dict[str, List[str]]
    traits: Dict[str, List[str]]
    expanded_terms: Set[str]
    warnings: List[str]


class GCIDEProvider:
    """
    Adapter to whatever GCIDE lookup you already have.
    You MUST edit `lookup()` to match your repo if needed.
    """

    def lookup(self, term: str) -> List[str]:
        try:
            # EDIT THIS IMPORT if your GCIDE function lives elsewhere
            from query.query_v2 import get_gcide_definitions
            defs = get_gcide_definitions(term)
            if not defs:
                return []
            if isinstance(defs, list):
                return [str(d) for d in defs]
            return [str(defs)]
        except Exception:
            return []


class SemanticProbe:
    def __init__(
        self,
        stopwords: Optional[Set[str]] = None,
        max_traits: int = 12,
        min_len: int = 3,
    ):
        self.provider = GCIDEProvider()
        self.stopwords = stopwords or set()
        self.max_traits = max_traits
        self.min_len = min_len

        self.definition_glue = {
            "especially", "usually", "often", "something", "someone",
            "having", "with", "without", "used", "using", "made", "make",
            "form", "forms", "kind", "kinds", "type", "types"
        }

    def probe(self, query_terms: Iterable[str]) -> ProbeResult:
        definitions: Dict[str, List[str]] = {}
        traits: Dict[str, List[str]] = {}
        expanded: Set[str] = set()
        warnings: List[str] = []

        for qt in query_terms:
            term = norm(qt)
            if not term:
                continue

            defs = self.provider.lookup(term)
            definitions[term] = defs

            extracted = self._extract_traits(defs)
            traits[term] = extracted
            expanded.update(extracted)

            if not defs:
                warnings.append(f"No GCIDE definitions for '{term}'")

        return ProbeResult(
            definitions=definitions,
            traits=traits,
            expanded_terms=expanded,
            warnings=warnings,
        )

    def _extract_traits(self, defs: List[str]) -> List[str]:
        scores: Dict[str, float] = {}

        for d in defs:
            toks = tokenize(d)
            for i, t in enumerate(toks):
                if len(t) < self.min_len:
                    continue
                if t in self.stopwords:
                    continue
                if t in self.definition_glue:
                    continue
                boost = 1.0 + (0.3 if i < 8 else 0.0)
                scores[t] = scores.get(t, 0.0) + boost

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [t for t, _ in ranked[: self.max_traits]]


def print_probe_report(result: ProbeResult) -> None:
    print("\n=== PROBE REPORT (GCIDE → TRAITS) ===")

    for term in result.definitions:
        print(f"\nTerm: {term}")
        defs = result.definitions.get(term, [])
        if defs:
            for d in defs[:2]:
                d = " ".join(d.split())
                print(f"  def: {d[:220]}{'...' if len(d) > 220 else ''}")
        else:
            print("  def: (none)")

        tr = result.traits.get(term, [])
        if tr:
            print(f"  traits: {', '.join(tr)}")
        else:
            print("  traits: (none)")

    if result.warnings:
        print("\nWarnings:")
        for w in result.warnings:
            print(f"  - {w}")

    print(f"\nExpanded trait count: {len(result.expanded_terms)}")
