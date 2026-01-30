import json
import sys
import re
import uuid
print("query.py started")
from pathlib import Path
from collections import defaultdict
from scripts.prolog_reader import load_glosses

# File paths
DATA = Path("corpora/kjv/verses_enriched.json")
SESS = Path("sessions")
SESS.mkdir(exist_ok=True)

# Load data
verses = json.loads(DATA.read_text())
prolog_glosses = load_glosses()

# Show references if requested
SHOW_REFS = "--refs" in sys.argv
word_re = re.compile(r"[a-z]+")

# Keyword groups
PURPOSE = set("why wherefore purpose created sent called chosen will way truth life light love".split())
PROCESS = set("how make build go come speak create give take rise walk live follow".split())
DEFINE = set("what is are was were behold".split())
TIME = set("when day days year years time season hour night morning".split())
PLACE = set("where land city place mount river wilderness house garden earth heaven".split())
AGENT = set("who he she they man men people lord god jesus david israel".split())
OWNERSHIP = set("whose belong inheritance inherit given children house of".split())

def words(t):
    return word_re.findall(t.lower())

def detect_intent(q):
    q = q.lower().strip()
    for i in ["how many", "how much", "why", "how", "what", "when", "where", "who", "which", "whose"]:
        if q.startswith(i):
            return i
    return "why"

def show(v):
    if SHOW_REFS:
        loc = f'{v.get("book", "")} {v["chapter"]}:{v["verse"]}'
        print(loc.strip())
    print(v["text"])
    print()

def score(v, intent):
    w = words(v["text"])
    if intent == "why":
        return sum(1 for x in w if x in PURPOSE)*2 + v["agency"]*3 + v["compassion"]*2 + v["sentiment"]
    if intent == "how":
        return sum(1 for x in w if x in PROCESS)*2 + v["agency"]*3
    if intent == "what":
        return sum(1 for x in w if x in DEFINE)*2 + v["sentiment"]
    if intent == "when":
        return sum(1 for x in w if x in TIME)
    if intent == "where":
        return sum(1 for x in w if x in PLACE)
    if intent == "who":
        return sum(1 for x in w if x in AGENT) + v["agency"]*2
    if intent == "whose":
        return sum(1 for x in w if x in OWNERSHIP) + v["dominance"]
    return 0

def ask(q, sid):
    intent = detect_intent(q)
    scored = [(score(v, intent), v) for v in verses]
    scored = [x for x in scored if x[0] > 0]
    scored.sort(reverse=True, key=lambda x: x[0])
    top = [v for _, v in scored[:5]]

    print(f"--- Top Scripture Matches for: \"{q}\" ---\n")
    for v in top:
        show(v)

    print("--- Related Definitions from WordNet ---")
    shown = set()
    for v in top:
        for w in words(v["text"]):
            for syn_id, gloss in prolog_glosses.items():
                if w in gloss.lower() and gloss not in shown:
                    print(f"{w.upper()} → {gloss}")
                    shown.add(gloss)
            if len(shown) >= 5:
                break
        if len(shown) >= 5:
            break

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: query.py \"your question here\"")
        sys.exit()

    sid = uuid.uuid4().hex[:8]
    q = " ".join(x for x in sys.argv[1:] if x != "--refs")
    
    print("Loading verses...")
    verses = json.loads(DATA.read_text())
    print(f"Loaded {len(verses)} verses.")

    print("Loading WordNet glosses...")
    prolog_glosses = load_glosses()
    print(f"Loaded {len(prolog_glosses)} WordNet glosses.")

    print(f"Asking: {q}")
    ask(q, sid)
