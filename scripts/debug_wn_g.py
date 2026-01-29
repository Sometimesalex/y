from pathlib import Path

PROLOG_FILE = Path("prolog/wn_g.pl")

if not PROLOG_FILE.exists():
    print("File not found:", PROLOG_FILE.resolve())
    exit(1)

with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
    for i, line in enumerate(f):
        print(f"{i+1:04d}: {line.strip()}")
        if i >= 20:
            break
