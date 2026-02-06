#!/usr/bin/env python3

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "querycorpora"

if len(sys.argv) < 2:
    print('Usage: query_v2.py "your question"')
    sys.exit(1)

# Full question (allow spaces)
question = " ".join(sys.argv[1:])

# Run query_v3.py and capture EVERYTHING it prints
proc = subprocess.run(
    ["python3", "scripts/query_v3.py", question],
    capture_output=True,
    text=True
)

raw = proc.stdout

# Ensure output directory exists
OUT.mkdir(exist_ok=True)

# Timestamped file
ts = int(time.time())
path = OUT / f"{ts}.json"

# Save raw sensory dump verbatim
with open(path, "w", encoding="utf-8") as f:
    f.write(raw)

# Terminal: show sensory field + where it was written
if sys.stdout.isatty():
    print(raw)
    print("\nWritten:", path)
else:
    # Web bridge just needs the file path
    print(str(path))
