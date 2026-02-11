#!/usr/bin/env python3
"""
GCIDE.txt -> GCIDE.json converter (GCIDE 0.54 style)

Correctness targets (verified on CAT):
- Multi-line bracketed etymology: collect until closing ']'
- Sense markers at start-of-line even when followed by text:
    "2. (Naut.) (a) ..."  and  "3. A ..."
- Sub-sense markers on same line: "(a) ... (b) ..."
- Note: blocks can wrap across lines; keep them in notes
- Implicit sense 1 for entries with Defn: but no numbered senses (verbs, etc.)
- Basic "See ..." extraction
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator

HEADWORD_RE = re.compile(r'^[A-Z][A-Z -]*$')
POS_LINE_RE = re.compile(r'^[A-Z][A-Za-z"\'`-]*,')
ETYMO_SPLIT_RE = re.compile(r'\bEtym:\s*', re.IGNORECASE)

# Sense line WITH trailing content:
#  "1. (Zoöl.)"
#  "2. (Naut.) (a) A strong vessel ..."
#  "3. A double tripod ..."
SENSE_START_RE = re.compile(r'^(\d+)\.\s*(?:\(([^)]+)\))?\s*(.*)$')

# Sub-sense marker at start of a text chunk
SUBSENSE_START_RE = re.compile(r'^\(([a-z])\)\s*(.*)$')

DEFN_RE = re.compile(r'^Defn:\s*(.*)$')
NOTE_RE = re.compile(r'^Note:\s*(.*)$')

SEE_RE = re.compile(r'\bSee\s+([^.;]+)', re.IGNORECASE)
END_PARENS_RE = re.compile(r'\(([^)]+)\)\s*$')


def normalize_ws(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def iter_entries(lines: Iterator[str]) -> Iterator[List[str]]:
    entry: List[str] = []
    for line in lines:
        line = line.rstrip("\n")
        if HEADWORD_RE.match(line.strip()):
            if entry:
                yield entry
                entry = []
        entry.append(line)
    if entry:
        yield entry


def new_pos_block(header: Optional[str] = None) -> Dict:
    return {
        "header": header,
        "pos": None,
        "domain": None,
        "etymology": None,
        "senses": []
    }


def new_sense(n: int, domain: Optional[str]) -> Dict:
    return {
        "sense": n,
        "domain": domain,
        "definition": "",
        "notes": [],
        "see_also": [],
        "sub_senses": []  # {"label": "a", "definition": "", "notes": [], "see_also": []}
    }


def new_subsense(label: str) -> Dict:
    return {
        "label": label,
        "definition": "",
        "notes": [],
        "see_also": []
    }


def ensure_entry(current: Optional[Dict]) -> Dict:
    return current if current is not None else new_pos_block()


def ensure_sense(current: Dict, current_sense: Optional[Dict]) -> Dict:
    if current_sense is None:
        current_sense = new_sense(1, None)
        current["senses"].append(current_sense)
    return current_sense


def extract_see_also(text: str) -> List[str]:
    out: List[str] = []
    for m in SEE_RE.finditer(text):
        chunk = m.group(1).replace(" and ", ",")
        for p in [x.strip(" ,") for x in chunk.split(",")]:
            p = normalize_ws(p)
            if p:
                out.append(p.lower())
    return out


def dedupe_sorted(xs: List[str]) -> List[str]:
    return sorted(set([x for x in xs if x]))


def parse_pos_line(line: str) -> Tuple[Optional[str], Optional[str], Optional[str], bool]:
    """
    Return (pos, domain, ety_inline, ety_is_open_bracketed)
    """
    pos = None
    dom = None
    ety = None
    ety_open = False

    split = ETYMO_SPLIT_RE.split(line, maxsplit=1)
    left = split[0].strip()
    if len(split) == 2:
        ety = split[1].strip()
        # if bracketed and not closed, keep etymology mode on
        if "[" in ety and "]" not in ety:
            ety_open = True

    parts = left.split(",", 1)
    if len(parts) == 2:
        rest = parts[1].strip()
        rest = re.sub(r'\[[^\]]*\]', '', rest).strip()  # strip grammar bracket junk for POS
        m_dom = END_PARENS_RE.search(rest)
        if m_dom:
            dom = m_dom.group(1).strip()
            rest = END_PARENS_RE.sub("", rest).strip()
        pos = rest if rest else None

    return pos, dom, ety, ety_open


def add_def(target: Dict, text: str) -> None:
    text = normalize_ws(text)
    if not text:
        return
    if target["definition"]:
        target["definition"] += " " + text
    else:
        target["definition"] = text


def add_note(target: Dict, text: str) -> None:
    text = normalize_ws(text)
    if not text:
        return
    target["notes"].append(text)


def split_inline_subsenses_into(current_sense: Dict, text: str) -> Optional[Dict]:
    """
    If text contains "(a) ... (b) ..." style, split into sub_senses.
    Returns the last subsense (current).
    If no subsenses found, returns None.
    """
    # Find all "(x)" markers
    # We split by scanning for "(a)" etc and keeping chunks
    markers = list(re.finditer(r'(?:(?<=\s)|^)\(([a-z])\)\s*', text))
    if not markers:
        return None

    # Anything before first marker stays in main definition
    prefix = normalize_ws(text[:markers[0].start()])
    if prefix:
        add_def(current_sense, prefix)
        current_sense["see_also"].extend(extract_see_also(prefix))

    last_sub = None
    for i, m in enumerate(markers):
        label = m.group(1)
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        chunk = normalize_ws(text[start:end])

        sub = new_subsense(label)
        if chunk:
            sub["definition"] = chunk
            sub["see_also"].extend(extract_see_also(chunk))
        current_sense["sub_senses"].append(sub)
        last_sub = sub

    return last_sub


def parse_entry(entry_lines: List[str]) -> Tuple[str, List[Dict]]:
    headword = entry_lines[0].strip().lower()

    entries: List[Dict] = []
    current: Optional[Dict] = None
    current_sense: Optional[Dict] = None
    current_sub: Optional[Dict] = None

    in_etymology = False
    in_note = False
    note_target: Optional[Dict] = None  # sense or subsense

    for raw in entry_lines[1:]:
        line = raw.rstrip()
        if not line.strip():
            # blank ends note continuation
            in_note = False
            note_target = None
            continue

        # POS header
        if POS_LINE_RE.match(line):
            if current is not None:
                entries.append(current)

            current = new_pos_block(header=line.strip())
            current_sense = None
            current_sub = None
            in_etymology = False
            in_note = False
            note_target = None

            pos, dom, ety_inline, ety_open = parse_pos_line(line)
            current["pos"] = pos
            current["domain"] = dom
            if ety_inline:
                current["etymology"] = normalize_ws(ety_inline)
                in_etymology = ety_open  # stay in etymology if bracket not closed
            continue

        # Multi-line bracketed etymology continuation
        if in_etymology:
            current = ensure_entry(current)
            add = normalize_ws(line)
            if current["etymology"]:
                current["etymology"] = normalize_ws(current["etymology"] + " " + add)
            else:
                current["etymology"] = add
            if "]" in line:
                in_etymology = False
            continue

        # Standalone etymology line
        if line.startswith("Etym:"):
            current = ensure_entry(current)
            ety = normalize_ws(line.replace("Etym:", "", 1))
            current["etymology"] = ety
            if "[" in ety and "]" not in ety:
                in_etymology = True
            continue

        # Note continuation
        if in_note and note_target is not None:
            # Stop if a new structural marker begins
            if POS_LINE_RE.match(line) or SENSE_START_RE.match(line) or DEFN_RE.match(line) or NOTE_RE.match(line):
                in_note = False
                note_target = None
            else:
                # append to last note
                if note_target.get("notes"):
                    note_target["notes"][-1] = normalize_ws(note_target["notes"][-1] + " " + line.strip())
                    note_target["see_also"].extend(extract_see_also(line))
                    continue
                in_note = False
                note_target = None

        # Sense start (with trailing content!)
        m_s = SENSE_START_RE.match(line)
        if m_s:
            current = ensure_entry(current)

            sense_n = int(m_s.group(1))
            dom = m_s.group(2).strip() if m_s.group(2) else None
            rest = m_s.group(3).strip()

            current_sense = new_sense(sense_n, dom)
            current["senses"].append(current_sense)
            current_sub = None

            if rest:
                # rest may contain inline subsenses
                current_sub = split_inline_subsenses_into(current_sense, rest)
                if current_sub is None:
                    add_def(current_sense, rest)
                    current_sense["see_also"].extend(extract_see_also(rest))
            continue

        # Note:
        m_note = NOTE_RE.match(line)
        if m_note:
            current = ensure_entry(current)
            current_sense = ensure_sense(current, current_sense)

            note_text = normalize_ws(m_note.group(1))
            if current_sub is not None:
                add_note(current_sub, note_text)
                current_sub["see_also"].extend(extract_see_also(note_text))
                note_target = current_sub
            else:
                add_note(current_sense, note_text)
                current_sense["see_also"].extend(extract_see_also(note_text))
                note_target = current_sense

            in_note = True
            continue

        # Defn:
        m_def = DEFN_RE.match(line)
        if m_def:
            current = ensure_entry(current)
            current_sense = ensure_sense(current, current_sense)

            text = normalize_ws(m_def.group(1))
            current_sense["see_also"].extend(extract_see_also(text))

            # Defn text may contain inline subsenses
            current_sub = split_inline_subsenses_into(current_sense, text)
            if current_sub is None:
                add_def(current_sense, text)
            continue

        # Continuation line: attach to subsense if active, else sense.
        current = ensure_entry(current)
        current_sense = ensure_sense(current, current_sense)

        text = normalize_ws(line)
        if current_sub is not None:
            if current_sub["definition"]:
                current_sub["definition"] = normalize_ws(current_sub["definition"] + " " + text)
            else:
                current_sub["definition"] = text
            current_sub["see_also"].extend(extract_see_also(text))
        else:
            # If this line starts with "(a)" etc, begin a subsense
            m_sub = SUBSENSE_START_RE.match(text)
            if m_sub:
                label = m_sub.group(1)
                rest = m_sub.group(2)
                current_sub = new_subsense(label)
                if rest:
                    current_sub["definition"] = normalize_ws(rest)
                    current_sub["see_also"].extend(extract_see_also(rest))
                current_sense["sub_senses"].append(current_sub)
            else:
                add_def(current_sense, text)
                current_sense["see_also"].extend(extract_see_also(text))

    if current is not None:
        entries.append(current)

    # Cleanup: dedupe see_also
    for e in entries:
        for s in e.get("senses", []):
            s["see_also"] = dedupe_sorted(s.get("see_also", []))
            for sub in s.get("sub_senses", []):
                sub["see_also"] = dedupe_sorted(sub.get("see_also", []))

    return headword, entries


def main() -> None:
    src = Path("corpora/GCIDE/GCIDE.txt")
    out = Path("corpora/GCIDE/GCIDE.json")

    gcide: Dict = {"meta": {"source": "gcide-0.54"}, "entries": {}}

    with src.open(encoding="utf-8", errors="ignore") as f:
        for entry_lines in iter_entries(f):
            headword, parsed_entries = parse_entry(entry_lines)
            if parsed_entries:
                gcide["entries"].setdefault(headword, []).extend(parsed_entries)

    with out.open("w", encoding="utf-8") as f:
        json.dump(gcide, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(gcide['entries'])} headwords to {out}")


if __name__ == "__main__":
    main()
