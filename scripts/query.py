import json
import sys
from pathlib import Path

DATA = Path("corpora/kjv/verses_enriched.json")
verses = json.loads(DATA.read_text())

purpose_words = set("""
why wherefore created make made formed sent called chosen live life
purpose will way truth light love serve seek find
""".split())

def tokenize(t):
    return [w.lower() for w in t.split()]

def why_here(n=15):
    scored = []

    for v in verses:
        words = tokenize(v["text"])
        purpose_hits = sum(1 for w in words if w in purpose_words)

        score = (
            purpose_hits * 2
            + v["agency"] * 3
            + v["compassion"] * 2
            + v["sentiment"]
        )

        if score > 0:
            scored.append((score, v))

    scored.sort(reverse=True, key=lambda x: x[0])

    for s, v in scored[:n]:
        print(f'{v["chapter"]}:{v["verse"]}  score={round(s,4)}')
        print(v["text"])
        print()

def top(metric, n=10):
    rows = sorted(verses, key=lambda v: v.get(metric, 0), reverse=True)
    for v in rows[:n]:
        print(f'{v["chapter"]}:{v["verse"]} {metric}={v[metric]:.4f}')
        print(v["text"])
        print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Commands:")
        print("  why")
        print("  top <metric>")
        sys.exit()

    cmd = sys.argv[1]

    if cmd == "why":
        why_here()
    elif cmd == "top":
        top(sys.argv[2])
