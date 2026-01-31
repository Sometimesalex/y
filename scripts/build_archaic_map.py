import json
import re
from pathlib import Path
from collections import Counter, defaultdict

from prolog_reader import LocalWordNet

DATA = Path("corpora/kjv/verses_enriched.json")

ARCHAIC = [
"unto","ye","thee","thine","saith","spake","begat","whither","wherewith",
"whosoever","whoso","forasmuch","lo","sware","sitteth","didst","shouldest"
]

word_re = re.compile(r"[a-z]+")

STOPWORDS = set("""
i he she they we you thou him her them us my thy your his their our in on at to of and
be is was were been have hath had do did doth shall will would not a an that this these
""".split())

def words(t):
    return word_re.findall(t.lower())

print("Loading verses...")
verses = json.loads(DATA.read_text())

print("Tokenizing...")
VERSE_WORDS = [words(v["text"]) for v in verses]

print("Loading WordNet...")
wn = LocalWordNet()

# global frequencies
GLOBAL = Counter()
for wlist in VERSE_WORDS:
    GLOBAL.update(wlist)

TOTAL_GLOBAL = sum(GLOBAL.values())

print("Building mappings...\n")

mapping = {}

for archaic in ARCHAIC:
    LOCAL = Counter()

    for wlist in VERSE_WORDS:
        if archaic in wlist:
            LOCAL.update(wlist)

    if not LOCAL:
        continue

    candidates = []

    for w, lc in LOCAL.items():
        if w == archaic or w in STOPWORDS:
            continue

        if not wn.lookup(w):
            continue

        gc = GLOBAL[w]

        # contrastive score
        score = (lc / sum(LOCAL.values())) - (gc / TOTAL_GLOBAL)

        candidates.append((score, w))

    candidates.sort(reverse=True)

    top = [w for s, w in candidates[:5] if s > 0]

    if top:
        mapping[archaic] = top

print("ARCHAIC = {")
for k, v in mapping.items():
    print(f'    "{k}": {v},')
print("}")
