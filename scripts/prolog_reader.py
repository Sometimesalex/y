from pathlib import Path

PROLOG_FILE = Path("prolog/wn_g.pl")

def load_glosses():
    with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            print(f"LINE {i+1}: {repr(line)}")
            if i > 10:
                break
