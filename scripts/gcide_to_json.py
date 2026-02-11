#!/usr/bin/env python3

import json
import re
from pathlib import Path

# Headword lines are ALL CAPS, possibly with spaces or hyphens
HEADWORD_RE = re.compile(r'^[A-Z][A-Z -]*$')

# POS lines like:
#   Cat, n.
#   Cat, v. t.
POS_RE = re.compile(r'^[A-Z][a-z-]+,\s+([a-z. ]+)')


def iter_entries(lines):
    """
    Yield blocks of lines corresponding to one GCIDE headword entry.
    """
    entry = []

    for line in lines:
        line = line.rstrip("\n")

        if HEADWORD_RE.match(line.strip()):
            if entry:
                yield entry
                entry = []

        entry.append(line)

    if entry:
        yield entry


def parse_entry(entry_lines):
    """
    Parse one GCIDE entry (one headword, possibly multiple POS blocks).
    """
    headword = entry_lines[0].strip().lower()

    entries = []
    current = None
    current_sense = None

    for raw_line in entry_lines[1:]:
        line = raw_line.rstrip()

        if not line.strip():
            continue

        # POS line
        pos_match = POS_RE.match(line)
        if pos_match:
            if current:
                entries.append(current)

            current = {
                "pos": pos_match.group(1).strip(),
                "domain": None,
                "etymology": None,
                "senses": [],
                "notes": []
            }
            current_sense = None
            continue

        # Etymology
        if line.startswith("Etym:"):
            if current is None:
                current = {
                    "pos": None,
                    "domain": None,
                    "etymology": None,
                    "senses": [],
                    "notes": []
                }

            current["etymology"] = line.replace("Etym:", "").strip()
            continue

        # Numbered sense (e.g. "1." or "2. (Zoöl.)")
        sense_match = re.match(r'^(\d+)\.\s*(\(([^)]+)\))?', line)
        if sense_match:
            if current is None:
                # GCIDE SAFETY: create POS block implicitly
                current = {
                    "pos": None,
                    "domain": None,
                    "etymology": None,
                    "senses": [],
                    "notes": []
                }

            current_sense = {
                "sense": int(sense_match.group(1)),
                "domain": sense_match.group(3),
                "text": ""
            }
            current["senses"].append(current_sense)
            continue

        # Definition line
        if line.startswith("Defn:"):
            if current_sense:
                current_sense["text"] += line.replace("Defn:", "").strip()
            continue

        # Notes
        if line.startswith("Note:"):
            if current is None:
                current = {
                    "pos": None,
                    "domain": None,
                    "etymology": None,
                    "senses": [],
                    "notes": []
                }

            current["notes"].append(line.replace("Note:", "").strip())
            continue

        # Continuation line (definition wrapping)
        if current_sense:
            current_sense["text"] += " " + line.strip()

    if current:
        entries.append(current)

    return headword, entries


def main():
    src = Path("corpora/GCIDE/GCIDE.txt")
    out = Path("corpora/GCIDE/GCIDE.json")

    gcide = {
        "meta": {
            "source": "gcide-0.54"
        },
        "entries": {}
    }

    with src.open(encoding="utf-8", errors="ignore") as f:
        for entry_lines in iter_entries(f):
            headword, parsed_entries = parse_entry(entry_lines)
            if parsed_entries:
                gcide["entries"].setdefault(headword, []).extend(parsed_entries)

    with out.open("w", encoding="utf-8") as f:
        json.dump(gcide, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(gcide['entries'])} headwords to {out}")


if __name__ == "__main__":
    main()
