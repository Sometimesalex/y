import json
import sys
import re
from pathlib import Path
from collections import defaultdict

DATA = Path("corpora/kjv/verses_enriched.json")
verses = json.loads(DATA.read_text())

# Optional references
SHOW_REFS = "--refs" in sys.argv

word_re = re.compile(r"[a-z]+")

def words(t):
    return word_re.findall(t.lower())

# Intent vocabularies
PURPOSE = set("why wherefore purpose created sent called chosen will way truth life light love".split())
PROCESS = set("how make build go come speak create give take rise walk live follow".split())
DEFINE = set("what is are was were behold".split())
TIME = set("when day days year years time season hour night morning".split())
PLACE = set("where land city place mount river wilderness house garden earth heaven".split())
AGENT = set("who he she they man men people lord god jesus david israel".split())
OWNERSHIP = set("whose belong inheritance inherit given children house of".split())

# Detect intent from question
def detect_intent(q):
    q = q.lower().strip()
    for i in ["how many", "how much", "why", "how", "what", "when", "where", "who", "which", "whose"]:
        if q.startswith(i):
            return i
    return "why"

def show(v):
    if SHOW_REFS:
        loc = f'{v.get("book","")} {v["chapter"]}:{v["verse"]}'
        print(loc.strip())
    print(v["text"])
    print()

# Scoring per intent
def score(v, intent):
    w = words(v["text"])

    if intent == "why":
        return (
            sum(1 for x in w if x in PURPOSE) * 2
            + v["agency"] * 3
            + v["compassion"] * 2
            + v["sentiment"]
        )

    if intent == "how":
        return sum(1 for x in w if x in PROCESS) * 2 + v["agency"] * 3

    if intent == "what":
        return sum(1 for x in w if x in DEFINE) * 2 + v["sentiment"]

    if intent == "when":
        return sum(1 for x in w if x in TIME)

    if intent == "where":
        return sum(1 for x in w if x in PLACE)

    if intent == "who":
        return sum(1 for x in w if x in AGENT) + v["agency"] * 2

    if intent == "whose":
        return sum(1 for x in w if x in OWNERSHIP) + v["dominance"]

    # default
    return 0

# HOW MANY / HOW MUCH → quantitative answers
def quantify(q):
    q = q.lower()
    term = q.replace("how many", "").replace("how much", "").strip()
    if not term:
        print("Please specify what to count.")
        return

    matches = [v for v in verses if term in v["text"].lower()]
    print(f"Occurrences of '{term}':", len(matches))
    print()

    # Also show top few examples
    for v in matches[:5]:
        show(v)

# WHICH → comparison between two terms/books if present
def compare(q):
    parts = re.split(r"\bor\b", q.lower())
    if len(parts) < 2:
        print("Please provide two things to compare (e.g. 'which is more compassionate: genesis or matthew').")
        return

    a = parts[0].replace("which", "").strip()
    b = parts[1].strip()

    def subset(term):
        return [v for v in verses if term in (v.get("book","").lower() + " " + v["text"].lower())]

    A = subset(a)
    B = subset(b)

    if not A or not B:
        print("Could not find both comparison targets.")
        return

    def avg(metric, rows):
        return sum(v[metric] for v in rows) / len(rows)

    metrics = ["sentiment","dominance","compassion","violence","agency"]

    print(f"Comparison: {a} vs {b}")
    for m in metrics:
        print(m, round(avg(m,A),4), "vs", round(avg(m,B),4))

# Main ask handler
def ask(q, n=10):
    intent = detect_intent(q)

    print("intent:", intent)
    print()

    if intent in ["how many", "how much"]:
        quantify(q)
        return

    if intent == "which":
        compare(q)
        return

    scored = []
    for v in verses:
        s = score(v, intent)
        if s > 0:
            scored.append((s, v))

    scored.sort(reverse=True, key=lambda x: x[0])

    for s,v in scored[:n]:
        show(v)

# Explicit metric ranking (debug / exploration)
def top(metric, n=10):
    rows = sorted(verses, key=lambda v: v.get(metric,0), reverse=True)
    for v in rows[:n]:
        print(metric, round(v[metric],4))
        show(v)

# Keyword search
def find(term):
    term = term.lower()
    hits = [v for v in verses if term in v["text"].lower()]
    for v in hits[:10]:
        show(v)
    print("matches:", len(hits))

# Book-level stats (if book field exists later)
def stats(book):
    rows = [v for v in verses if book.lower() in v.get("book","").lower()]
    if not rows:
        print("Book not found")
        return
    metrics = ["sentiment","dominance","compassion","violence","agency"]
    print(book)
    for m in metrics:
        print(m, round(sum(v[m] for v in rows)/len(rows),4))

if __name__=="__n__":
    pass

if __name__=="__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  query.py \"question\"")
        print("  query.py top <metric>")
        print("  query.py find <word>")
        print("  query.py stats <book>")
        print("Add --refs to show chapter/verse.")
        sys.exit()

    cmd = sys.argv[1]

    if cmd == "top":
        top(sys.argv[2])
    elif cmd == "find":
        find(sys.argv[2])
    elif cmd == "stats":
        stats(" ".join(sys.argv[2:]))
    else:
        ask(" ".join(sys.argv[1:]))
