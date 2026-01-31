import re
from pathlib import Path

# Base folder containing all Prolog WordNet files
BASE = Path("prolog")

# ---------- REGEX PATTERNS ----------

# g(100001740,'some text').
GLOSS_PATTERN = re.compile(r"g\((\d+),'(.*)'\)\.")

# s(100017087,1,'god',n,1,0).
SENSE_PATTERN = re.compile(r"s\((\d+),\d+,'([^']+)',([a-z]),(\d+),")

# generic (123,456)
REL_PATTERN = re.compile(r"\((\d+),(\d+)")


# ---------- LOADERS ----------

def load_glosses():
    glosses = {}

    path = BASE / "wn_g.pl"
    print("Opening:", path.resolve())

    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            m = GLOSS_PATTERN.match(line)
            if not m:
                continue

            synset_id = m.group(1)
            gloss = m.group(2)

            # unescape single quotes
            gloss = gloss.replace("\\'", "'")

            glosses[synset_id] = gloss

    print("Loaded", len(glosses), "glosses")
    return glosses


def load_senses():
    senses = {}

    path = BASE / "wn_s.pl"
    print("Opening:", path.resolve())

    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = SENSE_PATTERN.search(line)
            if not m:
                continue

            synset, word, pos, sense = m.groups()
            word = word.lower()

            senses.setdefault(word, []).append({
                "synset": synset,
                "pos": pos,
                "sense": int(sense)
            })

    print("Loaded", sum(len(v) for v in senses.values()), "senses")
    return senses


def load_relations(filename):
    rel = {}

    path = BASE / filename
    print("Opening:", path.resolve())

    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = REL_PATTERN.search(line)
            if not m:
                continue

            a, b = m.groups()
            rel.setdefault(a, set()).add(b)

    print("Loaded", filename, "relations:", len(rel))
    return rel


# ---------- MAIN WORDNET CLASS ----------

class LocalWordNet:
    def __init__(self):
        print("Loading local Prolog WordNet...")

        self.glosses = load_glosses()
        self.senses = load_senses()

        self.hypernyms = load_relations("wn_hyp.pl")
        self.antonyms = load_relations("wn_ant.pl")
        self.similar = load_relations("wn_sim.pl")
        self.derivations = load_relations("wn_der.pl")

        # new semantic power
        self.entailments = load_relations("wn_ent.pl")
        self.causes      = load_relations("wn_cs.pl")
        self.attributes  = load_relations("wn_at.pl")
        self.instances   = load_relations("wn_ins.pl")

        # part-whole
        self.part_mer    = load_relations("wn_mp.pl")
        self.sub_mer     = load_relations("wn_ms.pl")
        self.mem_mer     = load_relations("wn_mm.pl")

        # morphology / grammar
        self.participles = load_relations("wn_ppl.pl")
        self.pertains    = load_relations("wn_per.pl")
        self.verb_groups = load_relations("wn_vgp.pl")
        self.frames      = load_relations("wn_fr.pl")

        print("WordNet ready.\n")

    def lookup(self, word):
        word = word.lower()
        results = []

        for s in self.senses.get(word, []):
            syn = s["synset"]

            results.append({
                "synset": syn,
                "pos": s["pos"],
                "sense": s["sense"],
                "gloss": self.glosses.get(syn),
                "hypernyms": list(self.hypernyms.get(syn, [])),
                "antonyms": list(self.antonyms.get(syn, [])),
                "similar": list(self.similar.get(syn, [])),
                "derivations": list(self.derivations.get(syn, []))
            })

        return results


# ---------- TEST ----------

if __name__ == "__main__":
    wn = LocalWordNet()

    test_word = "light"
    print(f"Lookup for '{test_word}':\n")

    data = wn.lookup(test_word)
    for entry in data:
        print(entry)
        print("-" * 40)
