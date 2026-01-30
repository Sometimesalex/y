import json
import sys
import re
import uuid
from pathlib import Path
from collections import defaultdict, deque

from prolog_reader import LocalWordNet

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

print("Tokenizing verses once (cache)...")
VERSE_WORDS = [words(v["text"]) for v in verses]
VOCAB = set()
for wlist in VERSE_WORDS:
    VOCAB.update(wlist)
print(f"Bible vocab size: {len(VOCAB)}")

print("Loading local WordNet...")
wn = LocalWordNet()

# Build synset -> words map (needed for hypernym fallback)
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

# ---------------- FALLBACK HELPERS ----------------

def normalize_term(term):
    """
    Return a list of candidate forms for a query term.
    Handles simple plural -> singular and a couple common endings.
    """
    t = term.lower()
    cands = [t]

    if len(t) > 3 and t.endswith("ies"):
        cands.append(t[:-3] + "y")  # ladies -> lady
    if len(t) > 3 and t.endswith("es"):
        cands.append(t[:-2])        # boxes -> box
    if len(t) > 3 and t.endswith("s"):
        cands.append(t[:-1])        # birds -> bird

    # de-dup while preserving order
    seen = set()
    out = []
    for x in cands:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def hypernym_fallback_words(term, max_depth=6, max_hits=6):
    """
    Given a term, climb WordNet hypernyms (is-a) and return candidate
    fallback words that actually appear in Bible VOCAB.
    """
    # try each normalized form until we get senses
    senses = []
    used_form = None
    for form in normalize_term(term):
        senses = wn.lookup(form)
        if senses:
            used_form = form
            break

    if not senses:
        return used_form, []  # no WordNet entry to climb

    # BFS up hypernym graph starting from all synsets of the term
    start_synsets = [m["synset"] for m in senses]
    q = deque([(syn, 0) for syn in start_synsets])
    seen = set(start_synsets)

    candidates = []
    while q:
        syn, depth = q.popleft()
        if depth >= max_depth:
            continue

        # Move up: syn -> hypernyms
        for parent in wn.hypernyms.get(syn, []):
            if parent in seen:
                continue
            seen.add(parent)
            q.append((parent, depth + 1))

            # Convert parent synset back into words (lemmas) and keep those in Bible
            for w in SYNSET_TO_WORDS.get(parent, []):
                if w in VOCAB and w not in STOPWORDS:
                    candidates.append(w)
                    if len(candidates) >= max_hits:
                        return used_form, candidates

    return used_form, candidates

def expand_query_terms(raw_terms):
    """
    raw_terms: list of query terms after stopword filtering
    returns (expanded_terms_set, mapping_dict)
    mapping_dict: original_term -> list of terms actually used for scripture matching
    """
    expanded = set()
    mapping = {}

    for t in raw_terms:
        # if term exists in bible, use it
        if t in VOCAB:
            mapping[t] = [t]
            expanded.add(t)
            continue

        # otherwise try hypernym fallback (via WordNet)
        used_form, cands = hypernym_fallback_words(t)

        if cands:
            # pick a few best candidates (already filtered to VOCAB)
            mapping[t] = cands[:3]
            expanded.update(mapping[t])
        else:
            # no fallback possible
            mapping[t] = []

    return expanded, mapping

# ---------------- MAIN QUERY ----------------

def ask(q, sid):
    intent = detect_intent(q)
    sess_file = SESS / f"{sid}.json"

    # session storage kept simple for now
    if sess_file.exists():
        sess = json.loads(sess_file.read_text())
    else:
        sess = {"q": q, "intent": intent}

    raw_terms = [w for w in words(q) if w not in STOPWORDS]

    expanded_terms, mapping = expand_query_terms(raw_terms)

    # Show how we expanded/fell back
    print("\nQuery terms:", raw_terms if raw_terms else "(none)")
    if mapping:
        print("Term mapping:")
        for k, v in mapping.items():
            if v:
                print(f"  {k} -> {v}")
            else:
                print(f"  {k} -> (no bible/wordnet match)")

    if not expanded_terms:
        print("\nNo usable terms found after stopword removal + fallback.")
        print("Try a different phrasing or a more general term.")
        return

    matched = []
    LOCAL_SENSES = defaultdict(int)

    for v, wlist in zip(verses, VERSE_WORDS):
        if any(term in wlist for term in expanded_terms):
            matched.append(v)

            # count senses for the expanded terms only
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
        print("\nNo matching verses found even after fallback terms.")
        return

    print("\n---\nContext-shifted meanings:\n")

    ranked = []
    local_total = sum(LOCAL_SENSES.values()) or 1

    for syn, lc in LOCAL_SENSES.items():
        gc = GLOBAL_SENSES.get(syn, 1)
        delta = (lc / local_total) - (gc / GLOBAL_TOTAL)
        ranked.append((delta, syn))

    ranked.sort(reverse=True)

    for delta, syn in ranked[:10]:
        gloss = wn.glosses.get(syn)
        if gloss:
            print(f"{delta:+.4f} — {gloss}")

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
