import re, json
from pathlib import Path

BASE = Path("corpora")
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

global_index = {}

verse_re = re.compile(r"^(\d+):(\d+)\s+(.*)")

for corpus_dir in BASE.iterdir():
    if not corpus_dir.is_dir():
        continue

    corpus = corpus_dir.name
    raw = corpus_dir / "raw.txt"
    if not raw.exists():
        continue

    text = raw.read_text(encoding="utf-8", errors="ignore")

    start = text.find("*** START")
    if start != -1:
        text = text[start:]

    verses = []
    current_book = "Unknown"
    current = None

    for line in text.splitlines():
        line = line.rstrip()

        if not line.strip():
            continue

        # Detect book headers (Gutenberg style)
        if line.isupper() and len(line) < 100:
            current_book = line.title()
            continue

        m = verse_re.match(line)
        if m:
            # Save previous verse
            if current:
                verses.append(current)

            current = {
                "corpus": corpus,
                "book": current_book,
                "chapter": int(m.group(1)),
                "verse": int(m.group(2)),
                "text": m.group(3).strip()
            }
        else:
            # continuation of previous verse
            if current:
                current["text"] += " " + line.strip()

    if current:
        verses.append(current)

    out = corpus_dir / "verses.json"
    out.write_text(json.dumps(verses, indent=2), encoding="utf-8")

    global_index[corpus] = len(verses)

(Path("output") / "index.json").write_text(json.dumps(global_index, indent=2), encoding="utf-8")

print("Built:", global_index)
