#!/usr/bin/env python3

import sys
import re
import json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]

# -----------------------------
# Stopwords (minimal set)
# -----------------------------
STOPWORDS = {
    "the","is","a","an","and","or","to","of","in","on","at","for","with",
    "when","where","why","how","should","would","could","i","you","he","she",
    "it","we","they","me","my","your","our","their","this","that","these","those"
}

# -----------------------------
# Tokenization
# -----------------------------
WORD_RE = re.compile(r"[a-zA-Z']+")

def extract_query_terms(text):
    words = WORD_RE.findall(text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]

# -----------------------------
# Simple Local WordNet wrapper
# -----------------------------
class LocalWordNet:
    def __init__(self, prolog_dir):
        self.prolog_dir = Path(prolog_dir)
        self.gloss = {}
        self.hyp = defaultdict(set)
        self.senses = defaultdict(set)

    def load(self):
        files = [
            "wn_g.pl",
            "wn_s.pl",
            "wn_hyp.pl",
        ]

        for fname in files:
            path = self.prolog_dir / fname
            if not path.exists():
                continue

            print("Opening:", path)

            with open(path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()

                    if fname == "wn_g.pl" and line.startswith("g("):
                        # g(synset,'gloss').
                        try:
                            inside = line[2:-2]
                            syn, gloss = inside.split(",",1)
                            self.gloss[syn] = gloss.strip("'")
                        except:
                            pass

                    elif fname == "wn_s.pl" and line.startswith("s("):
                        # s(synset,_,word,_,_,_).
                        try:
                            parts = line[2:-2].split(",")
                            syn = parts[0]
                            word = parts[2].strip("'")
                            self.senses[word].add(syn)
                        except:
                            pass

                    elif fname == "wn_hyp.pl" and line.startswith("hyp("):
                        # hyp(child,parent).
                        try:
                            inside = line[4:-2]
                            c,p = inside.split(",")
                            self.hyp[c].add(p)
                        except:
                            pass

        print("WordNet ready.")

    def get_lemmas(self, word):
        out = set()
        for syn in self.senses.get(word, []):
            for w, syns in self.senses.items():
                if syn in syns:
                    out.add(w)
        return out

    def get_hypernyms(self, word):
        out = set()
        for syn in self.senses.get(word, []):
            for h in self.hyp.get(syn, []):
                for w, syns in self.senses.items():
                    if h in syns:
                        out.add(w)
        return out


# -----------------------------
# Load corpora
# -----------------------------
def load_corpora():
    corpora = []

    corpora_dir = ROOT / "corpora"
    for path in corpora_dir.rglob("verses_enriched.json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            corpora.extend(data)

    print("Loaded", len(corpora), "verses.")
    return corpora


# -----------------------------
# Main
# -----------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: query_v2.py \"your question\"")
        return

    question = sys.argv[1]
    print("\nAsking:", question)

    query_terms = extract_query_terms(question)
    print("\nQuery terms:", query_terms)

    # Load WordNet
    wn = None
    try:
        wn = LocalWordNet(ROOT / "prolog")
        wn.load()
    except Exception as e:
        print("\nWordNet skipped (non-fatal):", e)

    # Semantic expansion
    expanded = set(query_terms)

    if wn:
        for t in query_terms:
            expanded |= set(wn.get_lemmas(t))
            expanded |= set(wn.get_hypernyms(t))

    query_terms = sorted(expanded)
    print("\nExpanded terms:", query_terms)

    verses = load_corpora()

    # -----------------------------
    # Naive matching (for now)
    # -----------------------------
    by_corpus = defaultdict(list)

    for v in verses:
        text = v.get("text","").lower()
        for t in query_terms:
            if t in text:
                by_corpus[v["corpus"]].append(v)
                break

    # -----------------------------
    # Output
    # -----------------------------
    for corpus, items in by_corpus.items():
        print("\n==============================")
        print("Corpus:", corpus)
        print("==============================\n")

        for v in items[:5]:
            ref = f"[{v.get('work_title','')}] {v.get('chapter','')}:{v.get('verse','')}"
            print(ref)
            print(v["text"])
            print()

if __name__ == "__main__":
    main()
