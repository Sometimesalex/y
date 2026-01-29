import json
import re
from pathlib import Path

BASE = Path("corpora")
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

# Matches chapter:verse like 3:16
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

    # Trim Gutenberg header if present
    start = text.find("*** START")
    if start != -1:
        text = text[start:]

    verses = []
    current_book = "Unknown"
    current = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Book headers (all caps lines)
        if line.isupper() and len(line) < 120 and ":" not in line:
            current_book = line.title()
            continue

        matches = list(marker.finditer(line))

        if matches:
            for i, m in enumerate(matches):
                chapter = int(m.group(1))
                verse = int(m.group(2))

                text_start = m.end()
                text_end = matches[i + 1].start() if i + 1 < len(matches) else len(line)

                chunk = line[text_start:text_end].strip()

                if current:
                    verses.append(current)

                current = {
                    "corpus": corpus,
                    "book": current_book,
                    "chapter": chapter,
                    "verse": verse,
                    "text": chunk
                }
        else:
            # Continuation of previous verse
            if current:
                current["text"] += " " + line

    if current:
        verses.append(current)

    out = corpus_dir / "verses.json"
    out.write_text(json.dumps(verses, indent=2), encoding="utf-8")

    global_index[corpus] = len(verses)

(Path("output") / "index.json").write_text(json.dumps(global_index, indent=2), encoding="utf-8")

print("Built:", global_index)
