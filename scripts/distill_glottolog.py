#!/usr/bin/env python3

from pathlib import Path
import configparser

ROOT = Path(__file__).resolve().parents[1]
TREE = ROOT / "corpora" / "human_flow" / "raw" / "databases" / "glottolog" / "languoids" / "tree"
OUT = ROOT / "corpora" / "human_flow" / "raw" / "human_flow_languages.txt"

nodes = {}

# First pass: read all nodes
for md in TREE.rglob("md.ini"):
    node_dir = md.parent
    node_id = node_dir.name

    cp = configparser.ConfigParser()
    try:
        cp.read(md, encoding="utf-8")
    except:
        continue

    if "core" not in cp:
        continue

    name = cp["core"].get("name", "").strip()
    level = cp["core"].get("level", "").strip()
    lat = cp["core"].get("latitude", "").strip()
    lon = cp["core"].get("longitude", "").strip()

    nodes[node_dir] = {
        "id": node_id,
        "name": name,
        "level": level,
        "lat": lat,
        "lon": lon,
    }

# Second pass: determine parents via directory ancestry
rows = []

for node_dir, data in nodes.items():
    parent_id = ""

    for parent in node_dir.parents:
        if parent in nodes:
            parent_id = nodes[parent]["id"]
            break

    rows.append(f"{data['id']}\t{data['name']}\t{data['level']}\t{parent_id}\t{data['lat']}\t{data['lon']}")

with open(OUT, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(r + "\n")

print("Written:", OUT)
print("Rows:", len(rows))
