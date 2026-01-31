import re
import json
from pathlib import Path

GCIDE_DIR = Path("corpora/gcide")
OUT = Path("corpora/gcide/gcide.json")

ent_re = re.compile(r"<ent>(.*?)</ent>", re.I)
def_re = re.compile(r"<def>(.*?)</def>", re.I | re.S)
tag_re = re.compile(r"<.*?>")

def clean(t):
    t = tag_re.sub("", t)
    return " ".join(t.split())

entries = {}

for f in GCIDE_DIR.glob("CIDE.*"):
    if len(f.name) != 6:
        continue

    print("Reading", f.name)

    txt = f.read_text(errors="ignore")

    pos = 0
    while True:
        m = ent_re.search(txt, pos)
        if not m:
            break

        word = clean(m.group(1)).lower()
        start = m.end()

        d = def_re.search(txt, start)
        if not d:
            pos = start
            continue

        definition = clean(d.group(1))

        if word and definition:
            entries.setdefault(word, []).append(definition)

        pos = d.end()

print("Entries:", len(entries))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(entries, indent=2))

print("Written:", OUT)
