from pathlib import Path
import re

PROLOG_FILE = Path("prolog/wn_g.pl")

pattern = re.compile(r"g\((\d+),\s*'(.+)'\)\.")

count = 0
with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
    for i, line in enumerate(f):
        line = line.strip()
        if pattern.match(line):
            count += 1
            print(f"Matched [{i}]: {line}")
            if count >= 5:
                break

print(f"\nTotal matches: {count}")
