from pathlib import Path

PROLOG_FILE = Path("prolog/wn_g.pl")

with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
    for i, line in enumerate(f):
        if i >= 10:
            break
        print(f"[{i}] {repr(line)}")
