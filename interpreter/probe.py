# interpreter/probe.py
"""
probe.py — "Semantic Probe Layer" for the Y project.

Goal:
- Use GCIDE (or any dictionary provider) to generate *hypotheses* about an object
  (traits / keywords / synonym-ish anchors) WITHOUT injecting GCIDE text into the
  interpreter graph.
- Output: expanded query term set + a human-readable probe report.

Design rules:
- GCIDE may generate hypotheses. Corpora generate conclusions.
- If GCIDE is unavailable, probe degrades gracefully (no expansion, clear report).

How it works:
1) Look up definitions for each query term via a pluggable provider.
2) Extract "trait tokens" from the definition text using simple heuristics.
3) Return expanded tokens to help corpus retrieval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple


_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z'\-]*")


def _norm(s: str) -> str:
    s = (s or "").strip().lower().replace("’", "'")
    return s


def _tokenise(s: str) -> List[str]:
    return [_norm(m.group(0)) for m in _TOKEN_RE.finditer(s or "")]


@dataclass
class ProbeResult:
    # query term -> list of definition strings (raw)
    definitions: Dict[str, List[str]]
    # query term -> extracted trait tokens
    traits: Dict[str, List[str]]
    # all expanded tokens (traits union)
    expanded_terms: Set[str]
    # diagnostics
    warnings: List[str]


class GCIDEProvider:
    """
    Provider interface: implement get_definitions(term)->List[str]
    This module ships with an "auto" provider that tries to import
    an existing GCIDE lookup function from your repo.
    """

    def get_definitions(self, term: str) -> List[str]:
        raise NotImplementedError


class AutoGCIDEProvider(GCIDEProvider):
    """
    Best-effort adapter: tries to locate a GCIDE lookup in the repo
    without hard-coding your architecture.

    You can replace this with a direct import once you know the real path.
    """

    def __init__(self) -> None:
        self._fn: Optional[Callable[[str], Sequence[str]]] = None
        self._warnings: List[str] = []
        self._try_bind()

    @property
    def warnings(self) -> List[str]:
        return list(self._warnings)

    def _try_bind(self) -> None:
        """
        Try several likely import paths. If none exist, we remain unbound.
        """
        candidates: List[Tuple[str, str]] = [
            # (module, attribute)
            ("query.query_v2", "get_gcide_definitions"),
            ("query.query", "get_gcide_definitions"),
            ("scripts.query_v2", "get_gcide_definitions"),
            ("gcide", "get_definitions"),
            ("gcide.gcide", "get_definitions"),
        ]

        for mod_name, attr in candidates:
            try:
                mod = __import__(mod_name, fromlist=[attr])
                fn = getattr(mod, attr, None)
                if callable(fn):
                    self._fn = fn  # type: ignore[assignment]
                    return
            except Exception:
                continue

        # If we reach here, nothing bound
        self._warnings.append(
            "GCIDE provider not found via auto-import. "
            "Probe will run with no dictionary expansion."
        )

    def get_definitions(self, term: str) -> List[str]:
        if not self._fn:
            return []
        try:
            out = self._fn(term)
            if out is None:
                return []
            # normalise to list[str]
            if isinstance(out, (list, tuple)):
                return [str(x) for x in out]
            return [str(out)]
        except Exception as e:
            self._warnings.append(f"GCIDE lookup failed for '{term}': {e}")
            return []


class SemanticProbe:
    """
    Extract "trait tokens" from dictionary definitions.
    This is deliberately simple and auditable.
    """

    def __init__(
        self,
        provider: Optional[GCIDEProvider] = None,
        stopwords: Optional[Set[str]] = None,
        max_traits_per_term: int = 16,
        min_token_len: int = 3,
    ) -> None:
        self.provider = provider or AutoGCIDEProvider()
        self.stopwords = stopwords or set()
        self.max_traits_per_term = max_traits_per_term
        self.min_token_len = min_token_len

        # lightweight “definition glue” words to drop even if not in global stopwords
        self._def_glue = {
            "especially", "particularly", "usually", "often", "typically",
            "something", "someone", "anything", "everything",
            "used", "using", "use", "made", "make", "making",
            "having", "with", "without", "also",
        }

    def probe(self, query_terms: Iterable[str]) -> ProbeResult:
        definitions: Dict[str, List[str]] = {}
        traits: Dict[str, List[str]] = {}
        expanded: Set[str] = set()
        warnings: List[str] = []

        # collect provider warnings if any
        if isinstance(self.provider, AutoGCIDEProvider):
            warnings.extend(self.provider.warnings)

        for qt in query_terms:
            term = _norm(qt)
            if not term:
                continue

            defs = self.provider.get_definitions(term)
            definitions[term] = defs

            extracted = self._extract_traits_from_definitions(defs)
            traits[term] = extracted

            expanded.update(extracted)

        return ProbeResult(
            definitions=definitions,
            traits=traits,
            expanded_terms=expanded,
            warnings=warnings,
        )

    def _extract_traits_from_definitions(self, defs: Sequence[str]) -> List[str]:
        """
        Heuristic trait extraction:
        - tokenize definitions
        - drop stopwords + glue
        - keep alphabetic tokens >= min length
        - score by within-def frequency with a small preference for early tokens
        """
        if not defs:
            return []

        counts: Dict[str, float] = {}
        for d in defs:
            toks = _tokenise(d)
            for idx, t in enumerate(toks):
                if len(t) < self.min_token_len:
                    continue
                if t in self.stopwords:
                    continue
                if t in self._def_glue:
                    continue
                # basic de-noise: drop quote artefacts and lone apostrophes
                if t in {"''", "'"}:
                    continue
                # scoring: frequency + slight boost for earlier terms
                boost = 1.0 + (0.25 if idx < 8 else 0.0)
                counts[t] = counts.get(t, 0.0) + boost

        ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        out = [t for t, _s in ranked[: self.max_traits_per_term]]
        return out


def format_probe_report(res: ProbeResult, max_defs: int = 2, max_traits: int = 16) -> str:
    lines: List[str] = []
    if res.warnings:
        lines.append("Probe warnings:")
        for w in res.warnings:
            lines.append(f"  - {w}")
        lines.append("")

    for term in sorted(res.definitions.keys()):
        defs = res.definitions.get(term, [])
        tr = res.traits.get(term, [])
        lines.append(f"GCIDE probe for: {term}")
        if defs:
            for d in defs[:max_defs]:
                one = " ".join((d or "").strip().split())
                if len(one) > 220:
                    one = one[:217] + "..."
                lines.append(f"  def: {one}")
        else:
            lines.append("  def: (none)")

        if tr:
            lines.append(f"  traits: {', '.join(tr[:max_traits])}")
        else:
            lines.append("  traits: (none)")
        lines.append("")

    lines.append(f"Expanded terms count: {len(res.expanded_terms)}")
    if res.expanded_terms:
        preview = ", ".join(sorted(list(res.expanded_terms))[:40])
        lines.append(f"Expanded preview: {preview}")
    return "\n".join(lines)
