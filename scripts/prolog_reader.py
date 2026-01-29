from pathlib import Path

PROLOG_FILE = Path("prolog/wn_g.pl")

def load_glosses():
    glosses = {}
    with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("g(") and line.endswith(")."):
                try:
                    # Remove g( and ).
                    inner = line[2:-2]
                    # Split once on comma (id, gloss)
                    synset_id, gloss = inner.split(",", 1)
                    gloss = gloss.strip().strip("'")
                    glosses[synset_id.strip()] = gloss
                except Exception as e:
                    print("Failed to parse:", line)
                    continue
    return glosses

if __name__ == "__main__":
    glosses = load_glosses()
    print(f"Loaded {len(glosses)} glosses.")
    print("Sample:")
    for k in list(glosses.keys())[:5]:
        print(k, ":", glosses[k])
