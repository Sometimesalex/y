#!/usr/bin/env python3

from pathlib import Path
from collections import defaultdict

class LocalWordNet:
    """
    Minimal local WordNet loader using Prolog .pl files.

    Provides:
      - expand_terms(words)
    """

    def __init__(self, prolog_dir):
        self.prolog_dir = Path(prolog_dir)

        self.gloss = defaultdict(list)
        self.senses = defaultdict(list)
        self.hypernyms = defaultdict(set)

        self._load()

    # -----------------------------

    def _load(self):
        # wn_g.pl  (gloss)
        g = self.prolog_dir / "wn_g.pl"
        if g.exists():
            print(f"Opening: {g}")
            with open(g, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("g("):
                        try:
                            inside = line[2:line.index(").")]
                            parts = inside.split(",", 2)
                            syn = parts[0].strip()
                            gloss = parts[2].strip().strip("'")
                            self.gloss[syn].append(gloss)
                        except:
                            pass

        # wn_s.pl (senses)
        s = self.prolog_dir / "wn_s.pl"
        if s.exists():
            print(f"Opening: {s}")
            with open(s, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("s("):
                        try:
                            inside = line[2:line.index(").")]
                            parts = inside.split(",")
                            syn = parts[0].strip()
                            word = parts[4].strip().strip("'")
                            self.senses[word].append(syn)
                        except:
                            pass

        # wn_hyp.pl (hypernyms)
        h = self.prolog_dir / "wn_hyp.pl"
        if h.exists():
            print(f"Opening: {h}")
            with open(h, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("hyp("):
                        try:
                            inside = line[4:line.index(").")]
                            a, b = inside.split(",")
                            self.hypernyms[a.strip()].add(b.strip())
                        except:
                            pass

        print("WordNet ready.")

    # -----------------------------

    def expand_terms(self, words, depth=1):
        """
        Expand words via senses + hypernyms (lightweight).
        """

        out = set(words)

        for w in list(words):
            for syn in self.senses.get(w, []):
                for h in self.hypernyms.get(syn, []):
                    # add gloss words if present
                    for g in self.gloss.get(h, []):
                        for token in g.lower().split():
                            if len(token) > 2:
                                out.add(token)

        return list(out)
