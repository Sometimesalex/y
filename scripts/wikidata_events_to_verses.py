#!/usr/bin/env python3

import json
import time
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "corpora" / "historical_events" / "verses_enriched.json"

ENDPOINT = "https://query.wikidata.org/sparql"

HEADERS = {
    "Accept": "application/sparql+json",
    "User-Agent": "y-corpora-builder/0.1"
}

CLASSES = {
    "war": "Q198",
    "empire": "Q4830453",
    "pandemic": "Q3024240",
    "discovery": "Q13442814",
    "invention": "Q151885",
    "industrialization": "Q22698"
}

BASE_QUERY = """
SELECT ?itemLabel ?year ?desc WHERE {{
  ?item wdt:P31/wdt:P279* wd:{qid} .

  OPTIONAL {{ ?item wdt:P585 ?time . }}
  OPTIONAL {{ ?item wdt:P571 ?time . }}

  BIND(year(?time) AS ?year)

  OPTIONAL {{ ?item schema:description ?desc FILTER(lang(?desc)="en") }}

  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 2000
"""

rows = []

for name, qid in CLASSES.items():
    print("Pulling:", name)

    q = BASE_QUERY.format(qid=qid)

    r = requests.post(ENDPOINT, data={"query": q}, headers=HEADERS)
    if r.status_code != 200:
        print("Failed:", name, r.status_code)
        continue

    data = r.json()

    for b in data["results"]["bindings"]:
        label = b.get("itemLabel", {}).get("value", "")
        year = b.get("year", {}).get("value", "")
        desc = b.get("desc", {}).get("value", "")

        if not label:
            continue

        text = f"{label} {desc}".strip()

        rows.append({
            "corpus": "historical_events",
            "work_title": "historical_events",
            "chapter": year,
            "verse": label,
            "text": text
        })

    # be polite
    time.sleep(2)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

print("Written:", OUT)
print("Rows:", len(rows))
