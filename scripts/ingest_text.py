import re, json
from pathlib import Path

BASE = Path("corpora")
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

global_index = {}

for corpus_dir in BASE.iterdir():
    if not corpus_dir.is_dir():
        continue

    corpus = corpus_dir.name
    raw = corpus_dir / "raw.txt"
    if not raw.exists():
        continue

    text = raw.read_text(encoding="utf-8", errors="ignore")

    # Trim Gutenberg header if present
    start = text.find("*** START")
    if start != -1:
        text = text[start:]

    verses = []
    current_book = "Unknown"

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Book header heuristic (works okay for Gutenberg KJV)
        if (
            len(line) < 80
            and not re.match(r"^\d+:\d+\s", line)
            and any(w in line for w in ["Book", "Gospel", "Epistle", "Revelation", "Psalms", "Proverbs"])
        ):
            current_book = line

        m = re.match(r"^(\d+):(\d+)\s+(.*)", line)
        if m:
            verses.append({
                "corpus": corpus,
                "book": current_book,
                "chapter": int(m.group(1)),
                "verse": int(m.group(2)),
                "text": m.group(3).strip()
            })

    out = corpus_dir / "verses.json"
    out.write_text(json.dumps(verses, indent=2), encoding="utf-8")

    global_index[corpus] = len(verses)

(Path("output") / "index.json").write_text(json.dumps(global_index, indent=2), encoding="utf-8")

print("Built:", global_index)
