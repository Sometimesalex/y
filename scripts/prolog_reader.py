import re
from pathlib import Path
from collections import defaultdict

PROLOG_FILE = Path("prolog/wn_g.pl")

def load_glosses():
    """
    Parses wn_g.pl and extracts synset glosses.
    Returns a dictionary mapping synset IDs to gloss strings.
    """
    glosses = {}
    pattern = re.compile(r"^g\((\d+),\d+,'([^']+)'\)\.")

    with PROLOG_FILE.open(encoding="utf-8") as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                synset_id = match.group(1)
                gloss = match.group(2)
                glosses[synset_id] = gloss

    return glosses

if __name__ == "__main__":
    glosses = load_glosses()
    print(f"Loaded {len(glosses)} glosses.")
    print("Sample:")
    for sid, gloss in list(glosses.items())[:5]:
        print(f"{sid}: {gloss}")
