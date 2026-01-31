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

# ---------------- STOPWORDS ----------------

STOPWORDS = set("""
what do you about think is are was were the a an and or of to in on for with as by at from
he she they them we us i me my your his her their our
""".split())

# ---------------- LOAD DATA ----------------

print("Loading verses...")
verses = json.loads(DATA.read_text())
print(f"Loaded {len(verses)} verses.")

print("Tokenizing verses once (cache) + archaic normalization...")
VERSE_WORDS = [normalize_archaic(words(v["text"])) for v in verses]

VOCAB = set()
for wlist in VERSE_WORDS:
    VOCAB.update(wlist)
print(f"Bible vocab size (with archaic bridge): {len(VOCAB)}")

print("Loading local WordNet...")
wn = LocalWordNet()

# Build synset -> words map
print("Building synset->words map...")
SYNSET_TO_WORDS = defaultdict(set)
for w, senses in wn.senses.items():
    for s in senses:
        SYNSET_TO_WORDS[s["synset"]].add(w)
print(f"Synset->words entries: {len(SYNSET_TO_WORDS)}")

# ---------------- GLOBAL BASELINE ----------------

print("Building global sense baseline...")

GLOBAL_SENSES = defaultdict(int)
for wlist in VERSE_WORDS:
    for w in wlist:
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

# ---------------- NORMALIZATION ----------------

def normalize_term(term):
    t = term.lower()
    cands = [t]

    if len(t) > 3 and t.endswith("ies"):
        cands.append(t[:-3] + "y")
    if len(t) > 3 and t.endswith("es"):
        cands.append(t[:-2])
    if len(t) > 3 and t.endswith("s"):
        cands.append(t[:-1])

    seen = set()
    out = []
    for x in cands:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

# ---------------- SEMANTIC GRAPH ----------------

def semantic_neighbors(synset, max_hops=1):
    out = set()

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

    frontier = {synset}

    for _ in range(max_hops):
        nxt = set()
        for s in frontier:
            for rel in rel_sets:
                for t in rel.get(s, []):
                    if t not in out:
                        nxt.add(t)
                        out.add(t)
        frontier = nxt

    return out

def hypernym_fallback_words(term, max_depth=6, max_hits=6):
    senses = []

    for form in normalize_term(term):
        senses = wn.lookup(form)
        if senses:
            break

    if not senses:
        return None, []

    start_synsets = [m["synset"] for m in senses]
    q = deque([(syn, 0) for syn in start_synsets])
    seen = set(start_synsets)

    candidates = []

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
                    candidates.append(w)
                    if len(candidates) >= max_hits:
                        return None, candidates

    return None, candidates

def expand_query_terms(raw_terms):
    expanded = set()
    mapping = {}

    for t in raw_terms:
        if t in VOCAB:
            mapping[t] = [t]
            expanded.add(t)
            continue

        senses = []
        for form in normalize_term(t):
            senses = wn.lookup(form)
            if senses:
                break

        if not senses:
            mapping[t] = []
            continue

        seed_synsets = [m["synset"] for m in senses]
        all_synsets = set(seed_synsets)

        for s in seed_synsets:
            all_synsets |= semantic_neighbors(s)

        _, hypers = hypernym_fallback_words(t)
        for w in hype
