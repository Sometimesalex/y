import re
from pathlib import Path

PROLOG_FILE = Path("prolog/wn_g.pl")

def load_glosses():
    glosses = {}
    pattern = re.compile(r"g\((\d+),\s*'(.*)'\)\.")

    with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                synset_id, gloss = match.groups()
                gloss = gloss.replace("\\'", "'")
                glosses[synset_id] = gloss

    return glosses

if __name__ == "__main__":
    glosses = load_glosses()
    print(f"Loaded {len(glosses)} glosses.")
    print("Sample:")
    for k in list(glosses.keys())[:5]:
        print(k, ":", glosses[k])
