import json
import sys
import re
import uuid
from pathlib import Path
from collections import defaultdict

from prolog_reader import LocalWordNet

DATA = Path("corpora/kjv/verses_enriched.json")
SESS = Path("sessions")
SESS.mkdir(exist_ok=True)

print("Loading verses...")
verses = json.loads(DATA.read_text())
print(f"Loaded {len(verses)} verses.")

print("Loading local WordNet...")
wn = LocalWordNet()

SHOW_REFS = "--refs" in sys.argv

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

def detect_intent(q):
    q = q.lower().strip()
    for i in ["how many", "how much", "why", "how", "what", "when", "where", "who", "which", "whose"]:
        if q.startswith(i):
            return i
    return "why"

def show(v):
    if SHOW_REFS:
        print(f"{v['book']} {v['chapter']}:{v['verse']} —", end=" ")
    print(v["text"])

def intent_to_theme(intent):
    mapping = {
        "why": "purpose",
        "how": "process",
        "what": "define",
        "when": "time",
        "where": "place",
        "who": "agent",
        "whose": "ownership"
    }
    return mapping.get(intent, "purpose")

def ask(q, sid):
    intent = detect_intent(q)
    sess_file = SESS / f"{sid}.json"

    if sess_file.exists():
        sess = json.loads(sess_file.read_text())
    else:
        sess = {"q": q, "intent": intent, "themes": defaultdict(int)}

    matched = []
    for v in verses:
        w = words(v["text"])
        if any(term in w for term in words(q)):
            matched.append(v)

    print("\nYou are being drawn toward:", intent_to_theme(intent))

    for v in matched[:5]:
        print()
        show(v)

    print("\n---\nSemantic meanings (WordNet):\n")

    for term in words(q):
        meanings = wn.lookup(term)

        if not meanings:
            continue

        print(f"\n[{term}]")

        for m in meanings[:3]:  # limit per word
            print(f"- ({m['pos']}) {m['gloss']}")

    sess_file.write_text(json.dumps(sess, indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question here\"")
        sys.exit()

    sid = uuid.uuid4().hex[:8]
    q = " ".join(x for x in sys.argv[1:] if x != "--refs")

    print(f"\nAsking: {q}")
    ask(q, sid)
