import json
import re
from pathlib import Path
from collections import Counter, defaultdict

from prolog_reader import LocalWordNet

DATA = Path("corpora/kjv/verses_enriched.json")

# paste your TRUE archaic list here (from last output)
ARCHAIC = [
"shall","unto","ye","thee","shalt","saith","thine","spake","smote","dwelt","begat",
"thyself","whosoever","wherein","lo","beside","hid","whither","didst","wherewith",
"ought","sware","forsaken","shouldest","whereof","cherubims","forasmuch","sitteth"
]

word_re = re.compile(r"[a-z]+")

STOPWORDS = set("""
the and of to that for his they is him them thy was which my their from when this were upon you
came had into her we your against if these our did what she among should whom nor took how than
gave those would without where until whose told seen died having cannot women began whether could
""".split())

def words(t):
    return word_re.findall(t.lower())

print("Loading verses...")
verses = json.loads(DATA.read_text())

print("Loading WordNet...")
wn = LocalWordNet()

print("Indexing verse contexts...")
contexts = defaultdict(list)

for v in verses:
    toks = words(v["text"])
    for a in ARCHAIC:
        if a in toks:
            contexts[a].extend(toks)

print("\nBuilding mappings...\n")

mapping = {}

for a, toks in contexts.items():
    cnt = Counter(toks)

    # remove self + stopwords + archaic
    for bad in STOPWORDS | set(ARCHAIC) | {a}:
        cnt.pop(bad, None)

    # keep only WordNet-known words
    modern = []
    for w, c in cnt.most_common():
        if wn.lookup(w):
            modern.append((w, c))
        if len(modern) >= 5:
            break

    if modern:
        mapping[a] = [w for w, _ in modern]

# emit python dict
print("ARCHAIC = {")
for k, v in mapping.items():
    print(f'    "{k}": {v},')
print("}")
