# interpreter/query_v2_adapter.py

from typing import List
from interpreter.essence import QueryV2Adapter, QueryHit


class QueryV2LiveAdapter(QueryV2Adapter):
    """
    Live adapter: bridges query_v2.py output into the semantic engine.
    The engine remains retrieval-agnostic.
    """

    def run(self, question: str) -> List[QueryHit]:
        # Local import prevents circular dependencies
        from scripts.query_v2 import run_query

        result = run_query(question)

        hits: List[QueryHit] = []

        # IMPORTANT:
        # Adjust these keys to EXACTLY match query_v2.py output
        for r in result.get("results", []):
            hits.append(
                QueryHit(
                    corpus_id=r["corpus"],          # e.g. "kjv", "quran", "law"
                    doc_id=r.get("doc_id", "na"),
                    text=r["text"],
                    score=r.get("score", 1.0),
                )
            )

        return hits
