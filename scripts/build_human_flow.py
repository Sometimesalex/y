#!/usr/bin/env python3

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LANG = ROOT / "corpora" / "human_flow" / "raw" / "human_flow_languages.txt"
PLACE = ROOT / "corpora" / "human_flow" / "raw" / "human_flow_places.txt"
OUT = ROOT / "corpora" / "human_flow" / "human_flow.txt"

events = []

# -----------------
# Languages
# -----------------
# Format:
# id | name | level | parent | lat | lon
# No dates -> t = 0 placeholder

with open(LANG, encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 6:
            continue

        id_, name, level, parent, lat, lon = parts[:6]
        events.append((0, f"language\t{id_}\t{name}\t{level}\t{parent}\t{lat}\t{lon}"))

# -----------------
# Places
# -----------------
# Format:
# pid | title | lat | lon | start | end
# BUT title may contain tabs, so we rebuild it.

with open(PLACE, encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 6:
            continue

        pid = parts[0]
        lat = parts[-4]
        lon = parts[-3]
        start = parts[-2]
        end = parts[-1]
        title = "\t".join(parts[1:-4])

        try:
            t = int(float(start))
        except:
            t = 0

        events.append((t, f"place\t{pid}\t{title}\t{lat}\t{lon}\t{start}\t{end}"))

# -----------------
# Sort by time
# -----------------

events.sort(key=lambda x: x[0])

# -----------------
# Write output
# -----------------

with open(OUT, "w", encoding="utf-8") as f:
    for t, row in events:
        f.write(f"{t}\t{row}\n")

print("Written:", OUT)
print("Rows:", len(events))
