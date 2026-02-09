#!/usr/bin/env python3

import subprocess
import sys
import time
from pathlib import Path
import re

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


# ============================================================
# NEW SYSTEM ADAPTATION (PURE, NO REORDERING)
# ============================================================

# --- Step 1: extract linear tokens from raw debug output ---
# This is intentionally dumb and faithful.
tokens = re.findall(r"[A-Za-z]+", raw)

debug_tokens_path = OUT / f"{ts}.debug.tokens.txt"
with open(debug_tokens_path, "w", encoding="utf-8") as f:
    f.write(" ".join(tokens))


# --- Step 2: remove non-verbal tokens (letters only, keep order) ---
def is_verbal(token: str) -> bool:
    return token.isalpha()

clean_tokens = [t.lower() for t in tokens if is_verbal(t)]

debug_clean_linear_path = OUT / f"{ts}.debug.cleaned_linear.txt"
with open(debug_clean_linear_path, "w", encoding="utf-8") as f:
    f.write(" ".join(clean_tokens))


# --- Step 3: paragraph rendering (NO grammar, NO reordering) ---
def tokens_to_paragraph(tokens, width=120):
    lines = []
    line = ""
    for t in tokens:
        if len(line) + len(t) + 1 > width:
            lines.append(line.strip())
            line = ""
        line += t + " "
    if line:
        lines.append(line.strip())
    return "\n".join(lines)

raw_paragraph = tokens_to_paragraph(clean_tokens)

debug_paragraph_path = OUT / f"{ts}.debug.paragraph_raw.txt"
with open(debug_paragraph_path, "w", encoding="utf-8") as f:
    f.write(raw_paragraph)


# --- Step 4: minimal grammatical rendering ---
# Grammar as constraint, not author.
def grammatical_render(tokens):
    text = " ".join(tokens)
    text = text.strip()
    if not text:
        return text
    text = text[0].upper() + text[1:]
    if not text.endswith("."):
        text += "."
    return text

final_text = grammatical_render(clean_tokens)

final_path = OUT / f"{ts}.final.grammared.txt"
with open(final_path, "w", encoding="utf-8") as f:
    f.write(final_text)


# --- Optional terminal visibility ---
if sys.stdout.isatty():
    print("\n--- DEBUG: CLEANED LINEAR TOKENS ---")
    print(debug_clean_linear_path)

    print("\n--- DEBUG: RAW PARAGRAPH (NO GRAMMAR) ---")
    print(debug_paragraph_path)

    print("\n--- FINAL: GRAMMATICALLY RENDERED ---")
    print(final_path)
