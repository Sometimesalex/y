from typing import List
from pathlib import Path
import json
import subprocess

from interpreter.essence import QueryV2Adapter, QueryHit


class QueryV2LiveAdapter(QueryV2Adapter):
    """
    Live adapter for query_v2.py.
    Executes the script, then loads the STRICT JSON artefact
    produced by convert_querycorpora_to_json.py.
    """

    def run(self, question: str) -> List[QueryHit]:
        # 1. Run query_v2 (raw output)
        subprocess.run(
            ["python", "scripts/query_v2.py", question],
            check=True
        )

        # 2. Run the converter (this is REQUIRED)
        subprocess.run(
            ["python", "scripts/convert_querycorpora_to_json.py"],
            check=True
        )

        # 3. Load the newest converted JSON
        qc_dir = Path("querycorpora")
        converted = sorted(
            qc_dir.glob("*.converted.json"),
            key=lambda p: p.stat().st_mtime
        )

        if not converted:
            raise RuntimeError("No converted querycorpora JSON found")

        latest = converted[-1]

        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)   # STRICT JSON ONLY

        hits: List[QueryHit] = []

        # 4. Adapt converted JSON → QueryHit
        for corpus_id, entries in data.get("corpora", {}).items():
            for e in entries:
                hits.append(
                    QueryHit(
                        corpus_id=corpus_id,
                        doc_id=e.get("ref", "unknown"),
                        text=e.get("text", ""),
                        score=e.get("score", 1.0),
                    )
                )

        return hits
