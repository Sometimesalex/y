import json
import sys
import re
import uuid
from pathlib import Path
from collections import defaultdict, deque

from prolog_reader import LocalWordNet
from archaic_map import normalize_archaic

DATA = Path("corpora/kjv/verses_enriched.json")
SESS = Path("sessions")
SESS.mkdir(exist_ok=True)

SHOW_REFS = "--refs" in sys.argv

word_re = re.compile(r"[a-z]+")

def words(t):
    return word_re.findall(t.lower())

STOPWORDS = set("""
what do you about think is are was were the a an and or of to in on for with as by at from
he she they them we us i me my your his her their our should
""".split())

print("Loading verses...")
verses = json.loads(DATA.read_text())
print(f"Loaded {len(verses)} verses.")

print("Tokenizing verses once (cache) + archaic + verb normalization...")
VERSE_WORDS = [normalize_archaic(words(v["text"])) for v in verses]

VOCAB = set()
for wlist in VERSE_WORDS:
    VOCAB.update(wlist)
print(f"Bible vocab size (with bridges): {len(VOCAB)}")

print("Loading local WordNet...")
wn = LocalWordNet()

print("Building synset->words map...")
SYNSET_TO_WORDS = defaultdict(set)
for w, senses in wn.senses.items():
    for s in senses:
        SYNSET_TO_WORDS[s["synset"]].add(w)
print(f"Synset->words entries: {len(SYNSET_TO_WORDS)}")

print("Building global sense baseline...")
GLOBAL_SENSES = defaultdict(int)
for wlist in VERSE_WORDS:
    for w in wlist:
        for m in wn.lookup(w):
            GLOBAL_SENSES[m["synset"]] += 1

GLOBAL_TOTAL = float(sum(GLOBAL_SENSES.values()))
print("Global baseline built:", GLOBAL_TOTAL)

def detect_intent(q):
    q = q.lower().strip()
    for i in ["how many", "how much", "why", "how", "what", "when", "where", "who", "which", "whose"]:
        if q.startswith(i):
            return i
    return "why"

def intent_to_theme(intent):
    return {
        "why": "purpose",
        "how": "process",
        "what": "define",
        "when": "time",
        "where": "place",
        "who": "agent",
        "whose": "ownership"
    }.get(intent, "purpose")

def show(v):
    if SHOW_REFS:
        print(f"{v['book']} {v['chapter']}:{v['verse']} —", end=" ")
    print(v["text"])

def expand_query_terms(raw_terms):
    expanded = set()
    mapping = {}

    for t in raw_terms:
        # ---------- HARD CORPUS GATE ----------
        # If the literal word never appears in the Bible, STOP.
        if t not in VOCAB:
            mapping[t] = []
            continue

        # otherwise allow normal expansion
        mapping[t] = [t]
        expanded.add(t)

    return expanded, mapping

def ask(q, sid):
    intent = detect_intent(q)

    raw_terms = [w for w in words(q) if w not in STOPWORDS and w != intent]

    expanded_terms, mapping = expand_query_terms(raw_terms)

    print("\nQuery terms:", raw_terms if raw_terms else "(none)")
    print("Term mapping:")
    for k, v in mapping.items():
        if v:
            print(f"  {k} -> {v}")
        else:
            print(f"  {k} -> (no bible match)")

    missing = [k for k, v in mapping.items() if not v]
    if missing:
        print("\nConcepts not present in this corpus:", missing)
        return

    matched = []
    LOCAL = defaultdict(int)
    SYNSET_VERSES = defaultdict(list)

    for v, wlist in zip(verses, VERSE_WORDS):
        if any(t in wlist for t in expanded_terms):
            matched.append(v)
            for tok in wlist:
                if tok in expanded_terms:
                    for m in wn.lookup(tok):
                        syn = m["synset"]
                        LOCAL[syn] += 1
                        SYNSET_VERSES[syn].append(v["text"])

    print("\nYou are being drawn toward:", intent_to_theme(intent))

    for v in matched[:5]:
        print()
        show(v)

    print("\n---\nContext-shifted meanings (Bible-derived clusters):\n")

    ranked = []
    local_total = sum(LOCAL.values()) or 1.0

    for syn, lc in LOCAL.items():
        gc = GLOBAL_SENSES.get(syn, 1)
        delta = (lc / local_total) - (gc / GLOBAL_TOTAL)
        ranked.append((delta, syn))

    ranked.sort(reverse=True)

    CLUSTERS = {}
    for delta, syn in ranked:
        verseset = tuple(SYNSET_VERSES[syn][:3])
        if verseset and verseset not in CLUSTERS:
            CLUSTERS[verseset] = delta

    for verseset, delta in list(CLUSTERS.items())[:5]:
        print(f"\n{delta:+.4f}")
        for t in verseset:
            print(" •", t)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question here\"")
        sys.exit()

    sid = uuid.uuid4().hex[:8]
    q = " ".join(x for x in sys.argv[1:] if x != "--refs")

    print(f"\nAsking: {q}")
    ask(q, sid)
