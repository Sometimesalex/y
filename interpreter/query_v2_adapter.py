from typing import List
from pathlib import Path
import json
import subprocess

from interpreter.essence import QueryV2Adapter, QueryHit


class QueryV2LiveAdapter(QueryV2Adapter):
    """
    Live adapter for query_v2.py.

    Pipeline:
      1. Run query_v2.py (raw output)
      2. Run convert_querycorpora_to_json.py
      3. Load newest *.converted.json
      4. Adapt → QueryHit
    """

    def run(self, question: str) -> List[QueryHit]:
        # --------------------------------------------------
        # 1. Run query_v2 (RAW output only)
        # --------------------------------------------------
        subprocess.run(
            ["python", "scripts/query_v2.py", question],
            check=True
        )

        # --------------------------------------------------
        # 2. Run converter (STRICT JSON is REQUIRED)
        # --------------------------------------------------
        subprocess.run(
            ["python", "scripts/convert_querycorpora_to_json.py"],
            check=True
        )

        # --------------------------------------------------
        # 3. Locate newest converted JSON
        # --------------------------------------------------
        qc_dir = Path("querycorpora")
        converted_files = sorted(
            qc_dir.glob("*.converted.json"),
            key=lambda p: p.stat().st_mtime
        )

        if not converted_files:
            raise RuntimeError(
                "Query adapter error: no *.converted.json found in querycorpora/"
            )

        latest = converted_files[-1]

        # --------------------------------------------------
        # 4. Load STRICT JSON (no recovery hacks)
        # --------------------------------------------------
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)

        # --------------------------------------------------
        # 5. Adapt → QueryHit
        # --------------------------------------------------
        hits: List[QueryHit] = []

        corpora = data.get("corpora", {})
        if not corpora:
            raise RuntimeError(
                f"Converted JSON has no 'corpora' entries: {latest}"
            )

        for corpus_id, entries in corpora.items():
            for e in entries:
                hits.append(
                    QueryHit(
                        corpus_id=corpus_id,
                        doc_id=e.get("ref", "unknown"),
                        text=e.get("text", ""),
                        score=float(e.get("score", 1.0)),
                    )
                )

        if not hits:
            raise RuntimeError(
                f"No QueryHit objects produced from {latest}"
            )

        return hits
