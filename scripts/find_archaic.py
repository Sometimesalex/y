import json
import re
from pathlib import Path
from collections import Counter

from prolog_reader import LocalWordNet

DATA = Path("corpora/kjv/verses_enriched.json")

word_re = re.compile(r"[a-z]+")

def words(t):
    return word_re.findall(t.lower())

def normalize_forms(w):
    out = {w}

    if w.endswith("eth"):
        out.add(w[:-3])
    if w.endswith("est"):
        out.add(w[:-3])
    if w.endswith("th"):
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

print("Counting KJV vocabulary...")
counter = Counter()
for v in verses:
    counter.update(words(v["text"]))

print("Loading WordNet...")
wn = LocalWordNet()

archaic = []

for w, c in counter.most_common():
    if c < 40:
        continue

    found = False

    for form in normalize_forms(w):
        if wn.lookup(form):
            found = True
            break

    if not found:
        archaic.append((w, c))

print("\nLikely TRUE archaic terms:\n")

for w, c in archaic[:200]:
    print(f"{w:15} {c}")
