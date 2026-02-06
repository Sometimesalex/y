#!/usr/bin/env python3

import json
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "corpora" / "historical_events" / "verses_enriched.json"

ENDPOINT = "https://query.wikidata.org/sparql"

HEADERS = {
    "Accept": "application/sparql+json",
    "User-Agent": "y-corpora-builder/0.1"
}

# We pull multiple classes at once:
# wars, empires/states, pandemics, discoveries/inventions, industrialization

SPARQL = """
SELECT ?item ?itemLabel ?year ?desc WHERE {
  VALUES ?cls {
    wd:Q198        # war
    wd:Q4830453   # historical empire
    wd:Q3024240   # pandemic
    wd:Q13442814  # scientific discovery
    wd:Q151885    # invention
    wd:Q22698     # industrial revolution / industrialization
  }

  ?item wdt:P31/wdt:P279* ?cls .

  OPTIONAL { ?item wdt:P585 ?time . }
  OPTIONAL { ?item wdt:P571 ?time . }

  BIND(year(?time) AS ?year)

  OPTIONAL { ?item schema:description ?desc FILTER(lang(?desc)="en") }

  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 5000
"""

print("Querying Wikidata...")

r = requests.post(ENDPOINT, data={"query": SPARQL}, headers=HEADERS)
r.raise_for_status()

data = r.json()

rows = []

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

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

print("Written:", OUT)
print("Rows:", len(rows))
