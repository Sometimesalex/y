import json
import re
from pathlib import Path

BASE = Path("corpora")
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

cv_inline = re.compile(r"^(\d+):(\d+)\s+(.*)")
cv_only = re.compile(r"^(\d+):(\d+)$")
v_only = re.compile(r"^(\d+)\s+(.*)")
chap = re.compile(r"^CHAPTER\s+(\d+)", re.I)

global_index = {}

for corpus_dir in BASE.iterdir():
    if not corpus_dir.is_dir():
        continue

    corpus = corpus_dir.name
    raw = corpus_dir / "raw.txt"
    if not raw.exists():
        continue

    lines = raw.read_text(errors="ignore").splitlines()

    verses = []
    current_book = "Unknown"
    current_chapter = None
    current = None
    pending = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.isupper() and len(line) < 120 and ":" not in line:
            current_book = line.title()
            continue

        m = chap.match(line)
        if m:
            current_chapter = int(m.group(1))
            continue

        m = cv_inline.match(line)
        if m:
            if current:
                verses.append(current)
            current_chapter = int(m.group(1))
            current = {
                "corpus": corpus,
                "book": current_book,
                "chapter": current_chapter,
                "verse": int(m.group(2)),
                "text": m.group(3)
            }
            continue

        m = cv_only.match(line)
        if m:
            if current:
                verses.append(current)
            current_chapter = int(m.group(1))
            pending = {
                "corpus": corpus,
                "book": current_book,
                "chapter": current_chapter,
                "verse": int(m.group(2)),
                "text": ""
            }
            current = pending
            continue

        m = v_only.match(line)
        if m and current_chapter is not None:
            if current:
                verses.append(current)
            current = {
                "corpus": corpus,
                "book": current_book,
                "chapter": current_chapter,
                "verse": int(m.group(1)),
                "text": m.group(2)
            }
            continue

        if current:
            if current["text"]:
                current["text"] += " " + line
            else:
                current["text"] = line

    if current:
        verses.append(current)

    (corpus_dir / "verses.json").write_text(json.dumps(verses, indent=2))
    global_index[corpus] = len(verses)

(Path("output") / "index.json").write_text(json.dumps(global_index, indent=2))

print(global_index)
