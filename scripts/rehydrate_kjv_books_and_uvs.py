import json
from pathlib import Path

SRC = Path("corpora/kjv/verses_enriched.backup.json")
DST = Path("corpora/kjv/verses_enriched.json")

BOOKS = [
    "Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth",
    "1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah","Esther","Job",
    "Psalms","Proverbs","Ecclesiastes","Song of Solomon","Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel",
    "Hosea","Joel","Amos","Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi",
    "Matthew","Mark","Luke","John","Acts","Romans","1 Corinthians","2 Corinthians","Galatians","Ephesians",
    "Philippians","Colossians","1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon",
    "Hebrews","James","1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation"
]

print("Loading backup...")
verses = json.loads(SRC.read_text())

out = []

book_idx = 0
prev_chapter = 0
prev_verse = 0

for v in verses:
    chap = int(v.get("chapter", 0))
    verse = int(v.get("verse", 0))

    # New book if chapter drops OR we see a fresh 1:1 after previous verses
    if chap < prev_chapter or (chap == 1 and verse == 1 and prev_verse > 1):
        book_idx += 1

    prev_chapter = chap
    prev_verse = verse

    if book_idx >= len(BOOKS):
        raise RuntimeError("Book index exceeded canonical list")

    book = BOOKS[book_idx]

    uv = dict(v)

    uv["corpus"] = "christianity_kjv"
    uv["tradition"] = "christianity"

    uv["work"] = book.lower().replace(" ", "_")
    uv["work_title"] = book

    uv["section"] = str(v.get("chapter", ""))
    uv["subsection"] = str(v.get("verse", ""))

    out.append(uv)

DST.write_text(json.dumps(out, indent=2))

print("Done.")
print("Books assigned:", book_idx + 1)
print("Verses:", len(out))
