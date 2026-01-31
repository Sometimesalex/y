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
he she they them we us i me my your his her their our should
""".split())

# ---------------- DOMAIN CONDITIONING ----------------

DOMAIN_REWARD = set("""
god lord jesus christ spirit soul breath created create earth dust heaven hell sin life living
""".split())

DOMAIN_PENALIZE = set("""
prison guard broadcast television concert ammunition bomb lincoln center opera copy type
""".split())

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
        return []

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
                        return candidates

    return candidates

def expand_query_terms(raw_terms):
    expanded = set()
    mapping = {}

    for t in raw_terms:
        # ---- out-of-corpus guard ----
        if t not in VOCAB and not wn.lookup(t):
            mapping[t] = []
            continue

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

        hypers = hypernym_fallback_words(t)

        candidates = []
        for syn in all_synsets:
            for w in SYNSET_TO_WORDS.get(syn, []):
                if w in VOCAB and w not in STOPWORDS:
                    candidates.append(w)

        candidates.extend(hypers)

        seen = set()
        final = []
        for w in candidates:
            if w not in seen:
                seen.add(w)
                final.append(w)
            if len(final) >= 4:
                break

        mapping[t] = final
        expanded.update(final)

    return expanded, mapping

# ---------------- MAIN QUERY ----------------

def ask(q, sid):
    intent = detect_intent(q)
    sess_file = SESS / f"{sid}.json"

    if sess_file.exists():
        sess = json.loads(sess_file.read_text())
    else:
        sess = {"q": q, "intent": intent}

    intent_word = intent.split()[0]
    raw_terms = [w for w in words(q) if w not in STOPWORDS and w != intent_word]

    expanded_terms, mapping = expand_query_terms(raw_terms)

    print("\nQuery terms:", raw_terms if raw_terms else "(none)")
    if mapping:
        print("Term mapping:")
        for k, v in mapping.items():
            if v:
                print(f"  {k} -> {v}")
            else:
                print(f"  {k} -> (no bible/wordnet match)")

    # ---- out-of-corpus reporting ----
    missing = [k for k, v in mapping.items() if not v]
    if missing:
        print("\nConcepts not present in this corpus:", missing)
        return

    if not expanded_terms:
        print("\nNo usable terms found.")
        return

    matched = []
    LOCAL_SENSES = defaultdict(int)
    SYNSET_VERSES = defaultdict(list)

    for v, wlist in zip(verses, VERSE_WORDS):
        if any(term in wlist for term in expanded_terms):
            matched.append(v)
            for tok in wlist:
                if tok in expanded_terms:
                    for m in wn.lookup(tok):
                        syn = m["synset"]
                        LOCAL_SENSES[syn] += 1
                        SYNSET_VERSES[syn].append(v["text"])

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

        if syn in wn.entailments:
            delta *= 1.4
        if syn in wn.causes:
            delta *= 1.4

        gloss = wn.glosses.get(syn, "") or ""
        gwords = set(words(gloss))

        if gwords & DOMAIN_REWARD:
            delta *= 1.15
        if gwords & DOMAIN_PENALIZE:
            delta *= 0.55

        ranked.append((delta, syn))

    ranked.sort(reverse=True)

    # -------- collapse duplicate verse clusters --------

    CLUSTERS = {}
    for delta, syn in ranked:
        verseset = tuple(SYNSET_VERSES.get(syn, [])[:3])
        if not verseset:
            continue
        if verseset not in CLUSTERS or delta > CLUSTERS[verseset][0]:
            CLUSTERS[verseset] = (delta, syn)

    collapsed = sorted(CLUSTERS.values(), reverse=True)

    for delta, syn in collapsed[:5]:
        print(f"\n{delta:+.4f}")
        seen = set()
        for t in SYNSET_VERSES.get(syn, []):
            if t not in seen:
                print(" •", t)
                seen.add(t)
            if len(seen) >= 3:
                break

    sess_file.write_text(json.dumps(sess, indent=2))

# ---------------- ENTRY ----------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question here\"")
        sys.exit()

    sid = uuid.uuid4().hex[:8]
    q = " ".join(x for x in sys.argv[1:] if x != "--refs")

    print(f"\nAsking: {q}")
    ask(q, sid)
