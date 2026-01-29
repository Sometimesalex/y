import json
import sys
import re
import uuid
from pathlib import Path
from collections import defaultdict

DATA = Path("corpora/kjv/verses_enriched.json")
SESS = Path("sessions")
SESS.mkdir(exist_ok=True)

verses = json.loads(DATA.read_text())

SHOW_REFS = "--refs" in sys.argv

word_re = re.compile(r"[a-z]+")

def words(t):
    return word_re.findall(t.lower())

PURPOSE = set("why wherefore purpose created sent called chosen will way truth life light love".split())
PROCESS = set("how make build go come speak create give take rise walk live follow".split())
DEFINE = set("what is are was were behold".split())
TIME = set("when day days year years time season hour night morning".split())
PLACE = set("where land city place mount river wilderness house garden earth heaven".split())
AGENT = set("who he she they man men people lord god jesus david israel".split())
OWNERSHIP = set("whose belong inheritance inherit given children house of".split())

def detect_intent(q):
    q=q.lower().strip()
    for i in ["how many","how much","why","how","what","when","where","who","which","whose"]:
        if q.startswith(i):
            return i
    return "why"

def show(v):
    if SHOW_REFS:
        loc=f'{v.get("book","")} {v["chapter"]}:{v["verse"]}'
        print(loc.strip())
    print(v["text"])
    print()

def score(v,intent):
    w=words(v["text"])
    if intent=="why":
        return sum(1 for x in w if x in PURPOSE)*2+v["agency"]*3+v["compassion"]*2+v["sentiment"]
    if intent=="how":
        return sum(1 for x in w if x in PROCESS)*2+v["agency"]*3
    if intent=="what":
        return sum(1 for x in w if x in DEFINE)*2+v["sentiment"]
    if intent=="when":
        return sum(1 for x in w if x in TIME)
    if intent=="where":
        return sum(1 for x in w if x in PLACE)
    if intent=="who":
        return sum(1 for x in w if x in AGENT)+v["agency"]*2
    if intent=="whose":
        return sum(1 for x in w if x in OWNERSHIP)+v["dominance"]
    return 0

def load_session(sid):
    f=SESS/f"{sid}.json"
    if f.exists():
        return json.loads(f.read_text())
    return {"history":[],"themes":defaultdict(int)}

def save_session(sid,data):
    (SESS/f"{sid}.json").write_text(json.dumps(data,indent=2))

def summarize(rows):
    theme=defaultdict(int)
    for v in rows:
        for w in words(v["text"]):
            if w in PURPOSE: theme["purpose"]+=1
            if w in PROCESS: theme["process"]+=1
            if w in AGENT: theme["agent"]+=1
    return sorted(theme.items(),key=lambda x:x[1],reverse=True)

def ask(q,sid):
    sess=load_session(sid)
    intent=detect_intent(q)

    scored=[(score(v,intent),v) for v in verses]
    scored=[x for x in scored if x[0]>0]
    scored.sort(reverse=True,key=lambda x:x[0])

    top=[v for _,v in scored[:10]]

    sess["history"].append({"q":q,"intent":intent})
    themes=summarize(top)
    for k,v in themes:
        sess["themes"][k]+=v

    save_session(sid,sess)

    # faith voice summary
    if themes:
        print("You are being drawn toward:",", ".join(t for t,_ in themes[:2]))
        print()

    for v in top[:5]:
        show(v)

def quantify(q):
    term=q.lower().replace("how many","").replace("how much","").strip()
    hits=[v for v in verses if term in v["text"].lower()]
    print(f"There are {len(hits)} occurrences related to '{term}'.")
    print()
    for v in hits[:5]:
        show(v)

def compare(q):
    parts=re.split(r"\bor\b",q.lower())
    if len(parts)<2:
        print("Please provide two things to compare.")
        return
    a=parts[0].replace("which","").strip()
    b=parts[1].strip()
    A=[v for v in verses if a in v["text"].lower()]
    B=[v for v in verses if b in v["text"].lower()]
    if not A or not B:
        print("Could not resolve comparison.")
        return
    def avg(m,r): return sum(v[m] for v in r)/len(r)
    print("Comparison:")
    for m in ["sentiment","compassion","violence","agency"]:
        print(m,round(avg(m,A),4),"vs",round(avg(m,B),4))

if __name__=="__main__":
    if len(sys.argv)<2:
        print("Usage: query.py \"question\"")
        sys.exit()

    sid=uuid.uuid4().hex[:8]
    q=" ".join([x for x in sys.argv[1:] if x!="--refs"])

    intent=detect_intent(q)

    if intent in ["how many","how much"]:
        quantify(q)
    elif intent=="which":
        compare(q)
    else:
        ask(q,sid)
