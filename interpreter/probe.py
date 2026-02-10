"""
probe.py — Semantic Probe Layer (GCIDE-backed)

GCIDE ROLE:
- Hypothesis generator only
- Extract traits from definitions
- Never defines meaning
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Set, Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
GCIDE_PATH = ROOT / "corpora" / "GCIDE" / "gcide.json"

WORD_RE = re.compile(r"[a-zA-Z']+")


def norm(s: str) -> str:
    return (s or "").lower().strip()


def tokenize(text: str) -> List[str]:
    return WORD_RE.findall(text.lower())


@dataclass
class ProbeResult:
    definitions: Dict[str, List[str]]
    traits: Dict[str, List[str]]
    expanded_terms: Set[str]
    warnings: List[str]


class GCIDEProvider:
    """
    Direct GCIDE loader.
    This matches your existing implementation exactly.
    """

    def __init__(self):
        self.gcide = self._load_gcide()

    def _load_gcide(self) -> Dict[str, List[str]]:
        if not GCIDE_PATH.exists():
            return {}
        with open(GCIDE_PATH, encoding="utf-8") as f:
            return json.load(f)

    def lookup(self, term: str) -> List[str]:
        return self.gcide.get(term, [])


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
            "form", "forms", "kind", "kinds", "type", "types",
            "one", "who", "which", "that"
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

            if not defs:
                warnings.append(f"No GCIDE definitions for '{term}'")
                traits[term] = []
                continue

            extracted = self._extract_traits(defs)
            traits[term] = extracted
            expanded.update(extracted)

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
