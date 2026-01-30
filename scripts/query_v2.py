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

# ---------------- GLOBAL BASELINE ----------------

print("Building global sense baseline...")

GLOBAL_SENSES = defaultdict(int)

for v in verses:
    for w in words(v["text"]):
        for m in wn.lookup(w):
            GLOBAL_SENSES[m["synset"]] += 1

GLOBAL_TOTAL = sum(GLOBAL_SENSES.values())

print("Global baseline built:", GLOBAL_TOTAL)

# ---------------- INTENT ----------------

def detect_intent(q):
    q = q.lower().strip()
    for i in ["how many", "how much", "why", "how", "what", "when", "where", "who", "which", "whose"]:
        if q.startswith(i):
            return i
    return "why"

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

def show(v):
    if SHOW_REFS:
        print(f"{v['book']} {v['chapter']}:{v['verse']} —", end=" ")
    print(v["text"])

# ---------------- MAIN QUERY ----------------

def ask(q, sid):
    intent = detect_intent(q)
    sess_file = SESS / f"{sid}.json"

    if sess_file.exists():
        sess = json.loads(sess_file.read_text())
    else:
        sess = {"q": q, "intent": intent}

    matched = []
    LOCAL_SENSES = defaultdict(int)

    q_words = words(q)

    for v in verses:
        w = words(v["text"])
        if any(term in w for term in q_words):
            matched.append(v)

            verse_set = set(w)

            for tok in w:
                if tok in q_words:
                    best = None
                    best_score = 0

                    for m in wn.lookup(tok):
                        if not m["gloss"]:
                            continue

                        gloss_words = set(words(m["gloss"]))
                        score = len(gloss_words & verse_set)

                        i
