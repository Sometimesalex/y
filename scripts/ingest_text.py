import json
from pathlib import Path

BASE = Path("corpora")
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

def is_digit(c):
    return "0" <= c <= "9"

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

    i = 0
    n = len(text)

    while i < n:
        line_end = text.find("\n", i)
        if line_end == -1:
            line_end = n

        line = text[i:line_end].strip()
        i = line_end + 1

        if not line:
            continue

        if line.isupper() and len(line) < 100:
            current_book = line.title()
            continue

        j = 0
        L = len(line)

        found = False

        while j < L:
            if is_digit(line[j]):
                k = j
                while k < L and is_digit(line[k]):
                    k += 1

                if k < L and line[k] == ":":
                    k2 = k + 1
                    if k2 < L and is_digit(line[k2]):
                        while k2 < L and is_digit(line[k2]):
                            k2 += 1

                        chapter = int(line[j:k])
                        verse = int(line[k+1:k2])

                        t = k2
                        while t < L and line[t] == " ":
                            t += 1

                        if current:
                            verses.append(current)

                        current = {
                            "corpus": corpus,
                            "book": current_book,
                            "chapter": chapter,
                            "verse": verse,
                            "text": line[t:].strip()
                        }

                        found = True
                        break
                j += 1
            else:
                j += 1

        if not found and current:
            current["text"] += " " + line

    if current:
        verses.append(current)

    out = corpus_dir / "verses.json"
    out.write_text(json.dumps(verses, indent=2))

    global_index[corpus] = len(verses)

(Path("output") / "index.json").write_text(json.dumps(global_index, indent=2))

print(global_index)
