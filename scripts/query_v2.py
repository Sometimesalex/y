import json
import sys
import re
import uuid
from pathlib import Path
from collections import defaultdict

from prolog_reader import LocalWordNet
from archaic_map import normalize_archaic

DATA = Path("corpora/kjv/verses_enriched.json")
GCIDE_PATH = Path("corpora/GCIDE/gcide.json")
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

# Ontology ceiling: block human collapse for non-human queries
HUMAN_TERMS = {"man","men","woman","women","person","people","male","female"}

# ---------------- LOAD DATA ----------------

print("Loading verses...")
verses = json.loads(DATA.read_text())
print(f"Loaded {len(verses)} verses.")

print("Tokenizing verses once (cache) + archaic + verb normalization...")
VERSE_WORDS = [normalize_archaic(words(v["text"])) for v in verses]

VOCAB = set()
for wlist in VERSE_WORDS:
    VOCAB.update(wlist)
print(f"Bible vocab size (with bridges): {len(VOCAB)}")

# ---------------- LOAD GCIDE ----------------

GCIDE = {}
if GCIDE_PATH.exists():
    print("Loading GCIDE...")
    GCIDE = json.loads(GCIDE_PATH.read_text())
    GCIDE = {k.lower(): v for k, v in GCIDE.items()}
    print(f"GCIDE entries: {len(GCIDE)}")
else:
    print("GCIDE not found, skipping modern dictionary layer.")

# ---------------- WORDNET ----------------

print("Loading local WordNet...")
wn = LocalWordNet()

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

GLOBAL_TOTAL = float(sum(GLOBAL_SENSES.values()))
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

    out = []
    seen = set()
    for x in cands:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

# ---------------- SEMANTIC GRAPH ----------------

def semantic_neighbors(synset, max_hops=1):
    out = set()

    rel_sets = [
        getattr(wn, "entailments", {}),
        getattr(wn, "causes", {}),
        getattr(wn, "attributes", {}),
        getattr(wn, "instances", {}),
        getattr(wn, "part_mer", {}),
        getattr(wn, "sub_mer", {}),
        getattr(wn, "mem_mer", {}),
        getattr(wn, "verb_groups", {}),
        getattr(wn, "hypernyms", {}),
        getattr(wn, "hyp", {}),
        getattr(wn, "wn_hyp", {}),
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

# ---------------- QUERY EXPANSION ----------------

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

        noun_senses = [m for m in senses if m.get("pos") == "n"]

        # Upgrade 2: modern terms behave like nouns
        if noun_senses or t not in VOCAB:
            seed = noun_senses if noun_senses else senses
            hops = 2
        else:
            seed = senses
            hops = 1

        seed_synsets = [m["synset"] for m in seed]
        all_synsets = set(seed_synsets)

        for s in seed_synsets:
            all_synsets |= semantic_neighbors(s, max_hops=hops)

        candidates = []
        for syn in all_synsets:
            for w in SYNSET_TO_WORDS.get(syn, []):
                if w in VOCAB and w not in STOPWORDS:
                    # Upgrade 1: ontology ceiling
                    if t not in HUMAN_TERMS and w in HUMAN_TERMS:
                        continue
                    candidates.append(w)

        final = []
        seen = set()
        for w in candidates:
            if w not in seen:
                seen.add(w)
                final.append(w)
            if len(final) >= 4:
                break

        mapping[t] = final
        expanded.update(final)

    return expanded, mapping

# ---------------- GCIDE ----------------

def gcide_lookup(term):
    for form in normalize_term(term):
        if form in GCIDE:
            return GCIDE[form]
    return None

# ---------------- MAIN QUERY ----------------

def ask(q, sid):
    intent = detect_intent(q)
    raw_terms = [w for w in words(q) if w not in STOPWORDS]

    expanded_terms, mapping = expand_query_terms(raw_terms)

    # Per-term GCIDE fallback based on literal corpus absence
    gcide_hits = {}
    for t in raw_terms:
        if t not in VOCAB:
            defs = gcide_lookup(t)
            if defs:
                gcide_hits[t] = defs

    print("\nQuery terms:", raw_terms if raw_terms else "(none)")
    if mapping:
        print("Term mapping:")
        for k, v in mapping.items():
            print(f"  {k} -> {v if v else '(no bible match)'}")

    if gcide_hits:
        for t, defs in gcide_hits.items():
            print(f"\nGCIDE definition for '{t}':\n")
            for d in defs[:5]:
                print(" •", d.strip())

    if not expanded_terms:
        return

    matched = []
    LOCAL_SENSES = defaultdict(int)

    for v, wlist in zip(verses, VERSE_WORDS):
        if any(term in wlist for term in expanded_terms):
            matched.append(v)
            for tok in wlist:
                if tok in expanded_terms:
                    for m in wn.lookup(tok):
                        LOCAL_SENSES[m["synset"]] += 1

    print("\nYou are being drawn toward:", intent_to_theme(intent))

    if matched:
        for v in matched[:5]:
            print()
            show(v)
    else:
        print("\nNo matching verses found.")
        return

    print("\n---\nContext-shifted meanings (Bible-derived clusters):\n")

    ranked = []
    local_total = sum(LOCAL_SENSES.values()) or 1.0

    for syn, lc in LOCAL_SENSES.items():
        gc = GLOBAL_SENSES.get(syn, 1)
        delta = (lc / local_total) - (gc / GLOBAL_TOTAL)
        ranked.append((delta, syn))

    ranked.sort(reverse=True)

    for delta, syn in ranked[:5]:
        verses_here = []
        for v, wlist in zip(verses, VERSE_WORDS):
            if any(w in wlist for w in SYNSET_TO_WORDS.get(syn, [])):
                verses_here.append(v["text"])
            if len(verses_here) >= 3:
                break

        print(f"\n{delta:+.4f}")
        for t in verses_here:
            print(" •", t)

# ---------------- ENTRY ----------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question here\"")
        sys.exit()

    sid = uuid.uuid4().hex[:8]
    q = " ".join(x for x in sys.argv[1:] if x != "--refs")

    print(f"\nAsking: {q}")
    ask(q, sid)
