print("Loading verses...")
verses = json.loads(DATA.read_text())
print(f"Loaded {len(verses)} verses.")
print("Sample verse:", verses[0])

import json
import sys
import re
import uuid
from pathlib import Path
from collections import defaultdict
from scripts.prolog_reader import load_glosses

DATA = Path("corpora/kjv/verses_enriched.json")
SESS = Path("sessions")
SESS.mkdir(exist_ok=True)

word_re = re.compile(r"[a-z]+")

def words(t):
    return word_re.findall(t.lower())

PURPOSE = set("why wherefore purpose created sent called chosen will way truth life light love".split())
PROCESS = set("how make build go come speak create give take rise walk live follow".split())
DEFINE = set("what is are was were behold".split())
TIME = set("when day days year years time season hour night morning".split())
PLACE = set("where land city place mount river wilderness house garden earth heaven".split())
AGENT = set("who he she they man men people lord god jesus david israel".split())
OWNERSHIP = set("whose belong inheritance inherit given children house of".split())

CATEGORIES = {
    "purpose": PURPOSE,
    "process": PROCESS,
    "define": DEFINE,
    "time": TIME,
    "place": PLACE,
    "agent": AGENT,
    "ownership": OWNERSHIP
}

def detect_intent(q):
    q = q.lower().strip()
    for i in ["how many", "how much", "why", "how", "what", "when", "where", "who", "which", "whose"]:
        if q.startswith(i):
            return i
    return "unknown"

def show(v):
    if SHOW_REFS:
        print(v["ref"], "\t", v["text"])
    else:
        print(v["text"])

def ask(q, sid):
    qwords = set(words(q))
    intent = detect_intent(q)

    sess = {
        "q": q,
        "intent": intent,
        "themes": defaultdict(int)
    }

    results = []
    for v in verses:
        score = 0
        for w in words(v["text"]):
            for k, s in CATEGORIES.items():
                if w in s:
                    sess["themes"][k] += 1
                    score += 1
        if score > 0:
            results.append((score, v))

    results.sort(reverse=True, key=lambda x: x[0])
    sess_path = SESS / f"{sid}.json"
    sess_path.write_text(json.dumps(sess, indent=2))

    print("You are being drawn toward:", ", ".join(sorted(sess["themes"], key=sess["themes"].get, reverse=True)))
    print()

    for _, v in results[:5]:
        show(v)
        print()

    print("---")
    print("Related definitions from WordNet:")
    shown = set()
    for term in words(q):
        gloss = prolog_glosses.get(term)
        if not gloss:
            for k, g in prolog_glosses.items():
                if term in g and k not in shown:
                    gloss = g
                    shown.add(k)
                    break
        if gloss:
            print(f"{term}: {gloss}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: query.py \"your question here\"")
        sys.exit()

    sid = uuid.uuid4().hex[:8]
    q = " ".join(x for x in sys.argv[1:] if x != "--refs")

    SHOW_REFS = "--refs" in sys.argv

    print("Loading verses...")
    verses = json.loads(DATA.read_text())
    print(f"Loaded {len(verses)} verses.")

    print("Loading WordNet glosses...")
    prolog_glosses = load_glosses()
    print(f"Loaded {len(prolog_glosses)} WordNet glosses.")

    print(f"Asking: {q}")
    ask(q, sid)
