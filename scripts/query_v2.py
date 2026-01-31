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
BUT_ANALOG = True

word_re = re.compile(r"[a-z]+")

def words(t):
    return word_re.findall(t.lower())

STOPWORDS = set("""
what do you about think is are was were the a an and or of to in on for with as by at from
he she they them we us i me my your his her their our
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

def semantic_neighbors(synset, max_hops=1):
    rel_sets = [
        wn.entailments,
        wn.causes,
        wn.attributes,
        wn.instances,
        wn.part_mer,
        wn.sub_mer,
        wn.mem_mer,
        wn.verb_groups,
        wn.derivations,
    ]

    out = set()
    frontier = {synset}

    for _ in range(max_hops):
        nxt = set()
        for s in frontier:
            for rel in rel_sets:
                for t in rel.get(s, []):
                    if t not in out:
                        out.add(t)
                        nxt.add(t)
        frontier = nxt

    return out

def nearest_biblical_analogues(term, max_depth=6, max_hits=6):
    senses = wn.lookup(term)
    if not senses:
        return []

    start = [m["synset"] for m in senses]
    q = deque([(s, 0) for s in start])
    seen = set(start)

    out = []

    while q:
        syn, depth = q.popleft()
        if depth >= max_depth:
            continue

        for parent in wn.hypernyms.get(syn, []):
            if parent in seen:
                continue
            seen.add(parent)
            q.append((parent, depth + 1))

            for w in SYNSET_TO_WORDS.get(parent, []):
                if w in VOCAB and w not in STOPWORDS:
                    if w not in out:
                        out.append(w)
                        if len(out) >= max_hits:
                            return out
    return out

# ---------------- CORPUS-FIRST EXPANSION ----------------

def expand_query_terms(raw_terms):
    expanded = set()
    mapping = {}
    missing = []

    for t in raw_terms:
        # HARD CORPUS GATE
        if t not in VOCAB:
            mapping[t] = []
            missing.append(t)
            continue

        # in corpus → safe to expand
        mapping[t] = [t]
        expanded.add(t)

        senses = wn.lookup(t)
        seed = [m["synset"] for m in senses]

        for s in seed:
            for syn in semantic_neighbors(s):
                for w in SYNSET_TO_WORDS.get(syn, []):
                    if w in VOCAB and w not in STOPWORDS:
                        expanded.add(w)

    return expanded, mapping, missing

def ask(q, sid):
    intent = detect_intent(q)
    intent_word = intent.split()[0]

    raw_terms = [w for w in words(q) if w not in STOPWORDS and w != intent_word]

    expanded_terms, mapping, missing = expand_query_terms(raw_terms)

    print("\nQuery terms:", raw_terms if raw_terms else "(none)")
    print("Term mapping:")
    for k, v in mapping.items():
        if v:
            print(f"  {k} -> {v}")
        else:
            print(f"  {k} -> (no bible match)")

    if missing:
        print("\nConcepts not present in this corpus:", missing)

        if BUT_ANALOG:
            for t in missing:
                analogs = nearest_biblical_analogues(t)
                if analogs:
                    print(f"\nNearest biblical analogues for '{t}' (comparative, not equivalent):")
                    for a in analogs:
                        print(" •", a)

    if not expanded_terms:
        return

    matched = []
    LOCAL_SENSES = defaultdict(int)

    for v, wlist in zip(verses, VERSE_WORDS):
        if any(t in wlist for t in expanded_terms):
            matched.append(v)
            for tok in wlist:
                if tok in expanded_terms:
                    for m in wn.lookup(tok):
                        LOCAL_SENSES[m["synset"]] += 1

    print("\nYou are being drawn toward:", intent_to_theme(intent))

    if not matched:
        return

    for v in matched[:5]:
        print()
        show(v)

    print("\n---\nContext-shifted meanings (Bible-derived clusters):\n")

    ranked = []
    local_total = sum(LOCAL_SENSES.values()) or 1

    for syn, lc in LOCAL_SENSES.items():
        gc = GLOBAL_SENSES.get(syn, 1)
        delta = (lc / local_total) - (gc / GLOBAL_TOTAL)
        ranked.append((delta, syn))

    ranked.sort(reverse=True)

    for delta, syn in ranked[:5]:
        print(f"\n{delta:+.4f}")
        shown = 0
        for v, wlist in zip(verses, VERSE_WORDS):
            if shown >= 3:
                break
            if any(t in wlist for t in expanded_terms):
                print(" •", v["text"])
                shown += 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question here\"")
        sys.exit()

    sid = uuid.uuid4().hex[:8]
    q = " ".join(x for x in sys.argv[1:] if x != "--refs")

    print(f"\nAsking: {q}")
    ask(q, sid)
