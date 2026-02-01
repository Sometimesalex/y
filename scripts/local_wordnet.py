#!/usr/bin/env python3

from pathlib import Path
import re
from collections import defaultdict


class LocalWordNet:
    """
    Local Prolog WordNet loader.

    Loads:
      - wn_g.pl   (gloss)
      - wn_s.pl   (senses)
      - wn_hyp.pl (hypernyms)
      - wn_ant.pl (antonyms)
      - wn_sim.pl (similar)
      - wn_der.pl (derivations)

    Public API:
      senses_of(word)
      gloss_of(sid)
      hypernyms(sid)
      antonyms(sid)
      similars(sid)
      derivations(sid)
      expand_with_hypernym_fallback(sids, depth=1)
    """

    def __init__(self, prolog_dir):
        self.root = Path(prolog_dir)

        self.gloss = {}
        self.sense = defaultdict(list)

        self.hyper = defaultdict(set)
        self.ant = defaultdict(set)
        self.sim = defaultdict(set)
        self.der = defaultdict(set)

        self._load_gloss()
        self._load_sense()
        self._load_rel("wn_hyp.pl", self.hyper)
        self._load_rel("wn_ant.pl", self.ant)
        self._load_rel("wn_sim.pl", self.sim)
        self._load_rel("wn_der.pl", self.der)

        print("WordNet ready.\n")

    # ---------------- internal loaders ----------------

    def _open(self, name):
        path = self.root / name
        print(f"Opening: {path}")
        return open(path, "r", errors="ignore")

    def _load_gloss(self):
        count = 0
        with self._open("wn_g.pl") as f:
            for line in f:
                if not line.startswith("g("):
                    continue
                m = re.match(r"g\((\d+),'(.*)'\)\.", line)
                if m:
                    sid = int(m.group(1))
                    self.gloss[sid] = m.group(2)
                    count += 1
        print(f"Loaded {count} glosses")

    def _load_sense(self):
        count = 0
        with self._open("wn_s.pl") as f:
            for line in f:
                if not line.startswith("s("):
                    continue
                parts = line[2:].split(",")
                try:
                    sid = int(parts[0])
                    word = parts[4].strip("'").lower()
                    self.sense[word].append(sid)
                    count += 1
                except:
                    pass
        print(f"Loaded {count} senses")

    def _load_rel(self, fname, table):
        count = 0
        with self._open(fname) as f:
            for line in f:
                line = line.strip()
                if not line or "(" not in line:
                    continue
                try:
                    # works for hyp(1,2). ant(1,2). sim(1,2). der(1,2).
                    inside = line[line.index("(")+1:line.index(")")]
                    a, b = inside.split(",")[:2]
                    table[int(a.strip())].add(int(b.strip()))
                    count += 1
                except:
                    pass
        print(f"Loaded {fname} relations: {count}")

    # ---------------- public API ----------------

    def senses_of(self, word):
        return self.sense.get(word.lower(), [])

    def gloss_of(self, sid):
        return self.gloss.get(sid, "")

    def hypernyms(self, sid):
        return self.hyper.get(sid, set())

    def antonyms(self, sid):
        return self.ant.get(sid, set())

    def similars(self, sid):
        return self.sim.get(sid, set())

    def derivations(self, sid):
        return self.der.get(sid, set())

    def expand_with_hypernym_fallback(self, sids, depth=1):
        """
        Walk hypernyms upward so we always get something even if direct senses are sparse.
        Returns a list of synset ids.
        """
        seen = set(sids)
        frontier = set(sids)

        for _ in range(depth):
            nxt = set()
            for sid in frontier:
                for h in self.hyper.get(sid, set()):
                    if h not in seen:
                        seen.add(h)
                        nxt.add(h)
            frontier = nxt
            if not frontier:
                break

        return list(seen)
