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

    matches = list(marker.finditer(text))

    verses = []

    for i in range(len(matches)):
        m = matches[i]

        chapter = int(m.group(1))
        verse = int(m.group(2))

        content_start = m.end()
        content_end = matches[i+1].start() if i+1 < len(matches) else len(text)

        chunk = text[content_start:content_end]

        # Remove leading punctuation/whitespace
        chunk = chunk.lstrip(" .:-\n\r\t")

        verses.append({
            "corpus": corpus,
            "chapter": chapter,
            "verse": verse,
            "text": " ".join(chunk.split())
        })

    (corpus_dir / "verses.json").write_text(json.dumps(verses, indent=2))
    global_index[corpus] = len(verses)

(Path("output") / "index.json").write_text(json.dumps(global_index, indent=2))

print(global_index)
