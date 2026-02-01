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

GCIDE = {}
if GCIDE_PATH.exists():
    print("Loading GCIDE...")
    GCIDE = json.loads(GCIDE_PATH.read_text())
    GCIDE = {k.lower(): v for k, v in GCIDE.items()}
    print(f"GCIDE entries: {len(GCIDE)}")

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

GLOBAL_TOTAL = float(sum(GLOBAL_SENSES.values()) or 1.0)
print("Global baseline built:", GLOBAL_TOTAL)

def detect_intent(q):
    q = q.lower().strip()
    for i in ["how", "why", "what", "when", "where", "who", "which"]:
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
    }.get(intent, "purpose")

def show(v):
    if SHOW_REFS:
        work = v.get("work_title") or v.get("book", "")
        sec = v.get("section") or v.get("chapter", "")
        sub = v.get("subsection") or v.get("verse", "")
        print(f"{work} {sec}:{sub} —", end=" ")
    print(v["text"])

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

def gcide_lookup(term):
    for form in normalize_term(term):
        if form in GCIDE:
            return GCIDE[form]
    return None

def ask(q):
    intent = detect_intent(q)
    raw_terms = [w for w in words(q) if w not in STOPWORDS]

    print("\nQuery terms:", raw_terms if raw_terms else "(none)")

    gcide_hits = {}
    for t in raw_terms:
        defs = gcide_lookup(t)
        if defs:
            gcide_hits[t] = defs

    if gcide_hits:
        for t, defs in gcide_hits.items():
            print(f"\nGCIDE definition for '{t}':\n")
            for d in defs[:5]:
                print(" •", d.strip())

        if all(t not in VOCAB for t in raw_terms):
            return

    expanded = set()
    mapping = {}

    for t in raw_terms:
        if t in VOCAB:
            expanded.add(t)
            mapping[t] = [t]
            continue

        senses = []
        for form in normalize_term(t):
            senses = wn.lookup(form)
            if senses:
                break

        if not senses:
            mapping[t] = []
            continue

        candidates = []
        for m in senses:
            syn = m["synset"]
            for w in SYNSET_TO_WORDS.get(syn, []):
                if w in VOCAB:
                    candidates.append(w)

        final = []
        seen = set()
        for w in candidates:
            if w not in seen:
                seen.add(w)
                final.append(w)
            if len(final) >= 2:
                break

        mapping[t] = final
        expanded.update(final)

    if mapping:
        print("\nTerm mapping:")
        for k, v in mapping.items():
            print(f"  {k} -> {v if v else '(no bible match)'}")

    matched = []
    LOCAL_SENSES = defaultdict(int)

    for v, wlist in zip(verses, VERSE_WORDS):
        if any(term in wlist for term in expanded):
            matched.append(v)
            for tok in wlist:
                if tok in expanded:
                    for m in wn.lookup(tok):
                        LOCAL_SENSES[m["synset"]] += 1

    print("\nYou are being drawn toward:", intent_to_theme(intent))

    for v in matched[:5]:
        print()
        show(v)

    print("\n---\nContext-shifted meanings (Bible-derived clusters):\n")

    ranked = []
    local_total = sum(LOCAL_SENSES.values()) or 1.0

    for syn, lc in LOCAL_SENSES.items():
        gc = GLOBAL_SENSES.get(syn, 1)
        delta = (lc / local_total) - (gc / GLOBAL_TOTAL)
        ranked.append((delta, syn))

    ranked.sort(reverse=True)

    seen_syn = set()

    for delta, syn in ranked:
        if syn in seen_syn:
            continue
        seen_syn.add(syn)

        verses_here = []
        for v, wlist in zip(verses, VERSE_WORDS):
            if any(w in wlist for w in SYNSET_TO_WORDS.get(syn, [])):
                verses_here.append(v["text"])
            if len(verses_here) >= 3:
                break

        print(f"\n{delta:+.4f}")
        for t in verses_here:
            print(" •", t)

        if len(seen_syn) >= 5:
            break

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question here\"")
        sys.exit()

    q = " ".join(x for x in sys.argv[1:] if x != "--refs")
    print(f"\nAsking: {q}")
    ask(q)
