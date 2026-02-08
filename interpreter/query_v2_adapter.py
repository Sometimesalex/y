from typing import List
from pathlib import Path
import json
import subprocess
import time

from interpreter.essence import QueryV2Adapter, QueryHit


class QueryV2LiveAdapter(QueryV2Adapter):
    """
    Live adapter for query_v2.py.
    Executes the script, then loads the JSON artefact it produces.
    """

    def run(self, question: str) -> List[QueryHit]:
        # 1. Run query_v2 as a subprocess (do NOT import it)
        subprocess.run(
            ["python", "scripts/query_v2.py", question],
            check=True
        )

        # 2. Find the newest JSON file in querycorpora/
        qc_dir = Path("querycorpora")
        json_files = sorted(qc_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)

        if not json_files:
            raise RuntimeError("query_v2 produced no JSON output")

        latest = json_files[-1]

        # 3. Load JSON
        with open(latest, "r", encoding="utf-8") as f:
            raw = f.read()

        # Find the first JSON object in the file
        start = raw.find("{")
        end = raw.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise RuntimeError(f"No JSON object found in {latest}")

        data = json.loads(raw[start:end+1])


        hits: List[QueryHit] = []

        # 4. Adapt JSON → QueryHit
        # Adjust keys ONLY if needed — this matches your pipeline intent
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
