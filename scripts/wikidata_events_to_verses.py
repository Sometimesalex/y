#!/usr/bin/env python3

import json
import time
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "corpora" / "historical_events" / "verses_enriched.json"

ENDPOINT = "https://query.wikidata.org/sparql"

HEADERS = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "y-corpora-builder/0.1 (contact: local)"
}

CLASSES = {
    "war": "Q198",
    "pandemic": "Q3024240",
    "discovery": "Q13442814",
    "industrialization": "Q22698"
}

BASE_QUERY = """
SELECT ?itemLabel ?year ?desc WHERE {{
  ?item wdt:P31/wdt:P279* wd:{qid} .

  OPTIONAL {{ ?item wdt:P585 ?t1 . }}
  OPTIONAL {{ ?item wdt:P571 ?t2 . }}

  BIND(COALESCE(?t1, ?t2) AS ?time)
  BIND(year(?time) AS ?year)

  OPTIONAL {{ ?item schema:description ?desc FILTER(lang(?desc)="en") }}

  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 1000
"""

INVENTION_QUERY = """
SELECT ?itemLabel ?year ?desc WHERE {{
  ?item wdt:P31/wdt:P279* wd:Q151885 .

  OPTIONAL {{ ?item wdt:P571 ?time . }}
  BIND(year(?time) AS ?year)

  FILTER(?year >= {start} && ?year < {end})

  OPTIONAL {{ ?item schema:description ?desc FILTER(lang(?desc)="en") }}

  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 1000
"""

EMPIRE_QUERY = """
SELECT ?itemLabel ?year ?desc WHERE {{
  ?item wdt:P31/wdt:P279* wd:Q4830453 .

  OPTIONAL {{ ?item wdt:P571 ?time . }}
  BIND(year(?time) AS ?year)

  FILTER(?year >= {start} && ?year < {end})

  OPTIONAL {{ ?item schema:description ?desc FILTER(lang(?desc)="en") }}

  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 1000
"""

def run_query(session, query):
    for _ in range(2):
        try:
            r = session.post(ENDPOINT, data={"query": query}, timeout=60)
        except Exception:
            time.sleep(30)
            continue

        if r.status_code != 200:
            time.sleep(30)
            continue

        try:
            return r.json()
        except Exception:
            time.sleep(30)

    return None


def add_rows(rows, bindings):
    for b in bindings:
        label = b.get("itemLabel", {}).get("value", "")
        year = b.get("year", {}).get("value", "")
        desc = b.get("desc", {}).get("value", "")

        if not label:
            continue

        rows.append({
            "corpus": "historical_events",
            "work_title": "historical_events",
            "chapter": year,
            "verse": label,
            "text": f"{label} {desc}".strip()
        })


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    rows = []

    session = requests.Session()
    session.headers.update(HEADERS)

    # standard classes
    for name, qid in CLASSES.items():
        print("Pulling:", name)

        q = BASE_QUERY.format(qid=qid)
        data = run_query(session, q)

        if not data:
            print("Skipped:", name)
            continue

        bindings = data.get("results", {}).get("bindings", [])
        print("  received:", len(bindings))

        add_rows(rows, bindings)
        time.sleep(10)

    # empire sliced
    print("Pulling: empire (sliced)")

    for start in range(500, 2050, 100):
        end = start + 100
        print(f"  years {start}-{end}")

        q = EMPIRE_QUERY.format(start=start, end=end)
        data = run_query(session, q)

        if not data:
            continue

        bindings = data.get("results", {}).get("bindings", [])
        add_rows(rows, bindings)

        time.sleep(10)

    # invention sliced
    print("Pulling: invention (sliced)")

    for start in range(1600, 2050, 50):
        end = start + 50
        print(f"  years {start}-{end}")

        q = INVENTION_QUERY.format(start=start, end=end)
        data = run_query(session, q)

        if not data:
            continue

        bindings = data.get("results", {}).get("bindings", [])
        add_rows(rows, bindings)

        time.sleep(10)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print("Written:", OUT)
    print("Rows:", len(rows))


if __name__ == "__main__":
    main()
