import json
from collections import defaultdict
from pathlib import Path

from prolog_reader import LocalWordNet

OUT = Path("corpora/GCIDE/gcide.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

print("Loading WordNet...")
wn = LocalWordNet()

# Build synset -> words (same as query_v2.py)
print("Building synset->words map...")
SYNSET_TO_WORDS = defaultdict(set)
for w, senses in wn.senses.items():
    for s in senses:
        SYNSET_TO_WORDS[s["synset"]].add(w)

print("Synsets:", len(SYNSET_TO_WORDS))

print("Building GCIDE from WordNet glosses...")
gcide = defaultdict(list)

for synset, gloss in wn.glosses.items():
    if not gloss or not gloss.strip():
        continue

    for w in SYNSET_TO_WORDS.get(synset, []):
        gcide[w.lower()].append(gloss.strip())

# deduplicate definitions
final = {}
for k, defs in gcide.items():
    seen = []
    for d in defs:
        if d not in seen:
            seen.append(d)
    final[k] = seen

print("Entries:", len(final))

OUT.write_text(json.dumps(final, indent=2))
print("Written:", OUT)
