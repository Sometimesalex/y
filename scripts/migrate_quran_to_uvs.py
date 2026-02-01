import json
from pathlib import Path

SRC = Path("corpora/quran/quran_en.json")
OUT = Path("corpora/quran/verses_enriched.json")

with open(SRC) as f:
    surahs = json.load(f)

out = []

for s in surahs:
    surah_id = s["id"]
    name = s["transliteration"]
    title = s["translation"]

    for v in s["verses"]:
        out.append({
            "corpus": "islam_quran_en",
            "tradition": "islam",
            "work": name.lower().replace(" ", "-"),
            "work_title": name,
            "chapter": surah_id,
            "verse": v["id"],
            "section": str(surah_id),
            "subsection": str(v["id"]),
            "text": v["translation"],
            "sentiment": 0.0,
            "dominance": 0.0,
            "compassion": 0.0,
            "violence": 0.0,
            "agency": 0.0
        })

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))

print("Verses written:", len(out))
