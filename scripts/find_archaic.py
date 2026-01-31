import json
import re
from pathlib import Path
from collections import Counter

from prolog_reader import LocalWordNet

DATA = Path("corpora/kjv/verses_enriched.json")

word_re = re.compile(r"[a-z]+")

def words(t):
    return word_re.findall(t.lower())

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
    if c < 30:
        continue

    if not wn.lookup(w):
        archaic.append((w, c))

print("\nLikely archaic / out-of-WordNet terms:\n")

for w, c in archaic[:200]:
    print(f"{w:15} {c}")
