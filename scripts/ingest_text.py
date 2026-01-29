import json
import re
from pathlib import Path

BASE = Path("corpora")
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

marker = re.compile(r"(\d+):(\d+)")

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

    # detect book headers
    book_positions = []
    for m in re.finditer(r"\n([A-Z][A-Z\s]+)\n", text):
        book_positions.append((m.start(), m.group(1).title()))

    # collect all verse markers globally
    matches = list(marker.finditer(text))

    verses = []
    current_book = "Unknown"
    book_idx = 0

    for i, m in enumerate(matches):
        chapter = int(m.group(1))
        verse = int(m.group(2))

        start_text = m.end()
        end_text = matches[i+1].start() if i+1 < len(matches) else len(text)

        chunk = text[start_text:end_text]

        # update book by position
        while book_idx + 1 < len(book_positions) and book_positions[book_idx + 1][0] < m.start():
            book_idx += 1
            current_book = book_positions[book_idx][1]

        verses.append({
            "corpus": corpus,
            "book": current_book,
            "chapter": chapter,
            "verse": verse,
            "text": " ".join(chunk.split())
        })

    (corpus_dir / "verses.json").write_text(json.dumps(verses, indent=2))
    global_index[corpus] = len(verses)

(Path("output") / "index.json").write_text(json.dumps(global_index, indent=2))

print(global_index)
