import json
import re
from pathlib import Path
from collections import Counter

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
me it as but by or if why day even
""".split())

NARRATIVE = set("""
lord said saying god behold moses israel jacob abraham
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

def dominant_pos(word):
    senses = wn.lookup(word)
    if not senses:
        return None
    cnt = Counter(m["pos"] for m in senses)
    return cnt.most_common(1)[0][0]

print("\nBuilding refined mappings...\n")

mapping = {}

for archaic in ARCHAIC:
    LOCAL = Counter()

    for wlist in VERSE_WORDS:
        if archaic in wlist:
            LOCAL.update(wlist)

    if not LOCAL:
        continue

    archaic_pos = dominant_pos(archaic)

    scored = []

    for w, lc in LOCAL.items():
        if w == archaic or w in STOPWORDS or w in NARRATIVE:
            continue

        senses = wn.lookup(w)
        if not senses:
            continue

        if archaic_pos:
            wpos = dominant_pos(w)
            if wpos != archaic_pos:
                continue

        gc = GLOBAL[w]
        score = (lc / sum(LOCAL.values())) - (gc / TOTAL_GLOBAL)

        if score > 0:
            scored.append((score, w))

    scored.sort(reverse=True)

    top = [w for s, w in scored[:4]]

    if top:
        mapping[archaic] = top

print("ARCHAIC = {")
for k, v in mapping.items():
    print(f'    "{k}": {v},')
print("}")
