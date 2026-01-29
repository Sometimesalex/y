import re, json
from pathlib import Path

BASE = Path("corpora")
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

# matches 3:16 Some text
verse_marker = re.compile(r"(\d+):(\d+)\s+")

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
    current = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # detect book headers
        if line.isupper() and len(line) < 100:
            current_book = line.title()
            continue

        # find ALL verse markers in the line
        matches = list(verse_marker.finditer(line))

        if matches:
            for i, m in enumerate(matches):
                chapter = int(m.group(1))
                verse = int(m.group(2))
                start_idx = m.end()
                end_idx = matches[i+1].start() if i+1 < len(matches) else len(line)

                text_chunk = line[start_idx:end_idx].strip()

                if current:
                    verses.append(current)

                current = {
                    "corpus": corpus,
                    "book": current_book,
                    "chapter": chapter,
                    "verse": verse,
                    "text": text_chunk
                }
        else:
            # continuation of previous verse
            if current:
                current["text"] += " " + line

    if current:
        verses.append(current)

    out = corpus_dir / "verses.json"
    out.write_text(json.dumps(verses, indent=2))

    global_index[corpus] = len(verses)

(Path("output") / "index.json").write_text(json.dumps(global_index, indent=2))

print(global_index)
