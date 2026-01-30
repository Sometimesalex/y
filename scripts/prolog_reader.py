import re
from pathlib import Path

PROLOG_FILE = Path("prolog/wn_g.pl")

# matches:
# g(100001740,'some text').
PATTERN = re.compile(r"g\((\d+),'(.*)'\)\.")

def load_glosses():
    glosses = {}

    print("Opening:", PROLOG_FILE.resolve())

    with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            m = PATTERN.match(line)
            if not m:
                continue

            synset_id = m.group(1)
            gloss = m.group(2)

            # unescape single quotes if any
            gloss = gloss.replace("\\'", "'")

            glosses[synset_id] = gloss

    return glosses


if __name__ == "__main__":
    g = load_glosses()
    print("Loaded", len(g), "glosses")
    for k in list(g.keys())[:5]:
        print(k, ":", g[k])
