import re, json
from pathlib import Path

BASE = Path("corpora")
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

chapter_re = re.compile(r"^CHAPTER\s+(\d+)", re.I)
verse_re = re.compile(r"^(\d+)\s+(.*)")
colon_re = re.compile(r"^(\d+):(\d+)\s+(.*)")

global_index = {}

for corpus_dir in BASE.iterdir():
    if not corpus_dir.is_dir():
        continue

    corpus = corpus_dir.name
    raw = corpus_dir / "raw.txt"
    if not raw.exists():
        continue

    text = raw.read_text(errors="ignore")

    start = text.find("*** START")
    if start != -1:
        text = text[start:]

    verses = []
    current_book = "Unknown"
    current_chapter = None
    current = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Book headers
        if line.isupper() and len(line) < 100 and "CHAPTER" not in line:
            current_book = line.title()
            continue

        # Chapter headers
        m = chapter_re.match(line)
        if m:
            current_chapter = int(m.group(1))
            continue

        # Format: 3:16 For God so loved...
        m = colon_re.match(line)
        if m:
            if current:
                verses.append(current)

            current_chapter = int(m.group(1))
            current = {
                "corpus": corpus,
                "book": current_book,
                "chapter": current_chapter,
                "verse": int(m.group(2)),
                "text": m.group(3).strip()
            }
            continue

        # Format: 16 For God so loved...
        m = verse_re.match(line)
        if m and current_chapter is not None:
            if current:
                verses.append(current)

            current = {
                "corpus": corpus,
                "book": current_book,
                "chapter": current_chapter,
                "verse": int(m.group(1)),
                "text": m.group(2).strip()
            }
            continue

        # continuation line
        if current:
            current["text"] += " " + line

    if current:
        verses.append(current)

    out = corpus_dir / "verses.json"
    out.write_text(json.dumps(verses, indent=2))

    global_index[corpus] = len(verses)

(Path("output") / "index.json").write_text(json.dumps(global_index, indent=2))

print(global_index)
