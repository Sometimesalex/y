import json
import sys
from pathlib import Path
from collections import defaultdict

DATA = Path("corpora/kjv/verses_enriched.json")

verses = json.loads(DATA.read_text())

def top(metric, n=10):
    rows = sorted(verses, key=lambda v: v.get(metric, 0), reverse=True)
    for v in rows[:n]:
        print(f'{v["book"]} {v["chapter"]}:{v["verse"]} {metric}={v[metric]:.4f}')
        print(v["text"])
        print()

def book_stats(book):
    rows = [v for v in verses if book.lower() in v["book"].lower()]
    if not rows:
        print("Book not found")
        return

    metrics = ["sentiment","dominance","compassion","violence","agency"]
    out = {}

    for m in metrics:
        out[m] = sum(v[m] for v in rows) / len(rows)

    print(book)
    for k,v in out.items():
        print(k, round(v,4))

def list_books():
    books = sorted(set(v["book"] for v in verses))
    for b in books:
        print(b)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Commands:")
        print("  top <metric>")
        print("  book <name>")
        print("  books")
        sys.exit()

    cmd = sys.argv[1]

    if cmd == "top":
        top(sys.argv[2])
    elif cmd == "book":
        book_stats(" ".join(sys.argv[2:]))
    elif cmd == "books":
        list_books()
