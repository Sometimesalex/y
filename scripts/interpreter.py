#!/usr/bin/env python3

import json
import sys
from collections import Counter

WEIGHTS = {
    "kjv": 1.0,
    "quran": 1.0,
    "tanakh": 1.0,
    "historical_events": 0.6
}

def main(path):
    with open(path) as f:
        data = json.load(f)

    results = data.get("results", [])

    scores = []
    words = []

    for r in results:
        src = r.get("source", "")
        score = r.get("score", 0)
        text = r.get("text", "")

        weight = WEIGHTS.get(src, 0.5)
        scores.append(score * weight)

        words.extend(text.lower().split())

    avg = sum(scores) / max(len(scores), 1)
    common = Counter(words).most_common(15)

    print("\nInterpreter summary")
    print("-------------------")
    print("Signal strength:", round(avg, 3))
    print("\nDominant concepts:")

    for w, c in common:
        if len(w) > 4:
            print(" ", w)

    print("\nMessage:")
    print("Your query aligns most strongly with the themes above.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: interpreter.py results.json")
        sys.exit(1)

    main(sys.argv[1])
