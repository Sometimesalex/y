import ast
from pathlib import Path

PROLOG_FILE = Path("prolog/wn_g.pl")

def load_glosses():
    glosses = {}

    if not PROLOG_FILE.exists():
        print(f"ERROR: File {PROLOG_FILE} does not exist.")
        return glosses

    with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("g(") and line.endswith(")."):
                try:
                    content = line[2:-2]  # strip g( and ).
                    synset_id, gloss = content.split(",", 1)
                    gloss = ast.literal_eval(gloss.strip())
                    glosses[synset_id.strip()] = gloss
                except Exception as e:
                    print(f"Skipped line: {line}")
                    continue

    return glosses

if __name__ == "__main__":
    glosses = load_glosses()
    print(f"Loaded {len(glosses)} glosses.")
    print("Sample:")
    for k in list(glosses.keys())[:5]:
        print(k, ":", glosses[k])
