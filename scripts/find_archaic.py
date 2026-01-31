import json
import re
from pathlib import Path
from collections import Counter, defaultdict

from prolog_reader import LocalWordNet

DATA = Path("corpora/kjv/verses_enriched.json")

word_re = re.compile(r"[A-Za-z]+")

STOPWORDS = set("""
the and of to that for his they is him them thy was which my their from when this were upon you
came had into her we your against if these our did what she among should whom nor took how than
gave those would without where until whose told seen died having cannot women began whether could
else itself
""".split())

def words_raw(t):
    return word_re.findall(t)

def words(t):
    return [w.lower() for w in words_raw(t)]

def normalize_forms(w):
    out = {w}

    if w.endswith("eth"):
        out.add(w[:-3])
    if w.endswith("est"):
        out.add(w[:-3])
    if w.endswith("th"):
        out.add(w[:-2])
    if w.endswith("st"):
        out.add(w[:-2])

    if len(w) > 3 and w.endswith("s"):
        out.add(w[:-1])
    if len(w) > 3 and w.endswith("es"):
        out.add(w[:-2])
    if len(w) > 3 and w.endswith("ed"):
        out.add(w[:-2])
    if len(w) > 3 and w.endswith("ing"):
        out.add(w[:-3])

    return out

print("Loading verses...")
verses = json.loads(DATA.read_text())

print("Counting vocabulary + capitalization...")
counter = Counter()
caps = defaultdict(int)

for v in verses:
    raw = words_raw(v["text"])
    low = words(v["text"])
    for r, l in zip(raw, low):
        counter[l] += 1
        if r[0].isupper():
            caps[l] += 1

print("Loading WordNet...")
wn = LocalWordNet()

archaic = []

for w, c in counter.most_common():
    if c < 40:
        continue

    if w in STOPWORDS:
        continue

    # drop probable proper nouns (mostly capitalized)
    if caps[w] / c > 0.6:
        continue

    found = False
    for form in normalize_forms(w):
        if wn.lookup(form):
            found = True
            break

    if not found:
        archaic.append((w, c))

print("\nTRUE archaic surface forms:\n")

for w, c in archaic[:150]:
    print(f"{w:15} {c}")
