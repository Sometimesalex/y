import re
from pathlib import Path

PROLOG_FILE = Path("prolog/wn_g.pl")

def load_glosses():
    """
    Parses wn_g.pl and extracts synset glosses.
    Returns dict: synset_id -> gloss
    """
    glosses = {}

    # matches: g(100019046,'some text').
    pattern = re.compile(r"^g\((\d+),'(.*)'\)\.$")

    with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            m = pattern.match(line)
            if m:
                synset_id = m.group(1)
                gloss = m.group(2)
                glosses[synset_id] = gloss

    return glosses


if __name__ == "__main__":
    glosses = load_glosses()
    print(f"Loaded {len(glosses)} glosses.")
    print("Sample:")
    for k in list(glosses.keys())[:5]:
        print(k, ":", glosses[k])
