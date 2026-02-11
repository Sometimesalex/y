import json
import re
from pathlib import Path

HEADWORD_RE = re.compile(r'^[A-Z][A-Z -]*$')

def iter_entries(lines):
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
    headword = entry_lines[0].strip().lower()

    entries = []
    current = None
    current_sense = None

    for line in entry_lines[1:]:
        line = line.rstrip()

        # POS line
        if re.match(r'^[A-Z][a-z]+,', line):
            if current:
                entries.append(current)

            current = {
                "pos": None,
                "domain": None,
                "etymology": None,
                "senses": [],
                "notes": []
            }

            parts = line.split(',')
            current["pos"] = parts[1].strip()
            continue

        # Etymology
        if line.startswith("Etym:"):
            current["etymology"] = line.replace("Etym:", "").strip()
            continue

        # Sense number
        m = re.match(r'^(\d+)\.\s*(\(([^)]+)\))?', line)
        if m:
            current_sense = {
                "sense": int(m.group(1)),
                "domain": m.group(3),
                "text": ""
            }
            current["senses"].append(current_sense)
            continue

        # Definition
        if line.startswith("Defn:"):
            if current_sense:
                current_sense["text"] += line.replace("Defn:", "").strip()
            continue

        # Notes
        if line.startswith("Note:"):
            current["notes"].append(line.replace("Note:", "").strip())
            continue

        # Continuation lines
        if current_sense and line.strip():
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
            headword, parsed = parse_entry(entry_lines)
            if parsed:
                gcide["entries"].setdefault(headword, []).extend(parsed)

    with out.open("w", encoding="utf-8") as f:
        json.dump(gcide, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(gcide['entries'])} entries to {out}")


if __name__ == "__main__":
    main()
