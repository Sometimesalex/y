from pathlib import Path
import ast

PROLOG_FILE = Path("prolog/wn_g.pl")

def load_glosses():
    """
    Parses wn_g.pl and extracts synset glosses.
    Returns dict: synset_id -> gloss
    """
    glosses = {}

    with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()

            # match: g(100001740,'some text').
            if line.startswith("g(") and line.endswith(")."):
                try:
                    content = line[2:-2]  # remove g( and ).
                    synset_id, gloss = content.split(",", 1)
                    gloss = ast.literal_eval(gloss.strip())
                    glosses[synset_id.strip()] = gloss
                except:
                    continue

    return glosses


if __name__ == "__main__":
    glosses = load_glosses()
    print(f"Loaded {len(glosses)} glosses.")
    print("Sample:")
    for k in list(glosses.keys())[:5]:
        print(k, ":", glosses[k])
