import json
from pathlib import Path
import re

BASE = Path("corpora")

sent_pos = set("good blessed joy peace love mercy grace glad righteous".split())
sent_neg = set("evil wrath curse destroy sorrow fear weep death wicked".split())

dominance = set("command rule reign smite subdue destroy lord king obey servant master".split())
compassion = set("love mercy forgive heal help comfort give shelter feed".split())
violence = set("kill slew smite strike destroy blood war sword fire".split())
agency = set("make build go come speak create give take rise walk".split())

word_re = re.compile(r"[a-z]+")

def score(words, vocab):
    return sum(1 for w in words if w in vocab)

for corpus_dir in BASE.iterdir():
    verses_file = corpus_dir / "verses.json"
    if not verses_file.exists():
        continue

    verses = json.loads(verses_file.read_text())

    enriched = []

    for v in verses:
        words = word_re.findall(v["text"].lower())
        n = max(len(words), 1)

        v2 = dict(v)
        v2["sentiment"] = (score(words, sent_pos) - score(words, sent_neg)) / n
        v2["dominance"] = score(words, dominance) / n
        v2["compassion"] = score(words, compassion) / n
        v2["violence"] = score(words, violence) / n
        v2["agency"] = score(words, agency) / n

        enriched.append(v2)

    out = corpus_dir / "verses_enriched.json"
    out.write_text(json.dumps(enriched, indent=2))

    print(corpus_dir.name, "enriched:", len(enriched))
