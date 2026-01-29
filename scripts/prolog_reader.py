import ast
import re
from pathlib import Path

PROLOG_FILE = Path("prolog/wn_g.pl")

def load_glosses():
    """
    Parses wn_g.pl and extracts synset glosses.
    Returns dict: synset_id -> gloss
    """
    glosses = {}

    if not PROLOG_FILE.exists():
        print(f"❌ File not found at: {PROLOG_FILE.resolve()}")
        return glosses

    with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("g(") and line.endswith(")."):
                try:
                    content = line[2:-2]  # remove g( and ).
                    synset_id, gloss = content.split(",", 1)
                    gloss = ast.literal_eval(gloss.strip())  # safely evaluate string
                    glosses[synset_id.strip()] = gloss
                except Exception as e:
                    # Optional: print(f"Skipping line due to error: {e}")
                    continue
    return glosses

if __name__ == "__main__":
    glosses = load_glosses()
    print(f"Loaded {len(glosses)} glosses.")
    print("Sample:")
    for k in list(glosses.keys())[:5]:
        print(k, ":", glosses[k])
