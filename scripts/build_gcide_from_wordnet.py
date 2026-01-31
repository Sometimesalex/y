import json
from collections import defaultdict
from pathlib import Path

from prolog_reader import LocalWordNet

OUT = Path("corpora/GCIDE/gcide.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

print("Loading WordNet...")
wn = LocalWordNet()

# wn.glosses assumed loaded from wn_g.pl inside LocalWordNet
# format typically: synset -> gloss string

gcide = defaultdict(list)

print("Building GCIDE from WordNet glosses...")

for synset, gloss in wn.glosses.items():
    words = wn.synset_to_words.get(synset, [])
    for w in words:
        if gloss and gloss.strip():
            gcide[w.lower()].append(gloss.strip())

# deduplicate
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
