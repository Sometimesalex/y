import json
from pathlib import Path

SRC = Path("corpora/kjv/verses_enriched.json")
BACKUP = Path("corpora/kjv/verses_enriched.backup.json")

print("Loading KJV...")
verses = json.loads(SRC.read_text())

print("Backing up original...")
BACKUP.write_text(json.dumps(verses, indent=2))

out = []

for v in verses:
    book = v.get("book", "").strip()

    uv = dict(v)

    # Add Universal Verse Schema fields (non-destructive)
    uv["corpus"] = "christianity_kjv"
    uv["tradition"] = "christianity"

    uv["work"] = book.lower().replace(" ", "_")
    uv["work_title"] = book

    uv["section"] = str(v.get("chapter", ""))
    uv["subsection"] = str(v.get("verse", ""))

    out.append(uv)

SRC.write_text(json.dumps(out, indent=2))

print(f"Done. Migrated {len(out)} verses.")
print("Backup saved as:", BACKUP)
