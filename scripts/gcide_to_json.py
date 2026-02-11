#!/usr/bin/env python3
"""
GCIDE.txt -> GCIDE.json converter (GCIDE 0.54 style)

Goals:
- Lossless-ish dictionary capture without WordNet contamination
- Correct handling of:
  * POS lines with inline Etym:
  * Numbered senses (1., 2., ...)
  * Sub-senses (a), (b), (c)
  * Defn: blocks (including implicit sense 1 when no numbering exists)
  * Note: blocks attached to the current sense
  * Basic See ... cross-reference extraction
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator

# Headword lines are ALL CAPS, possibly with spaces or hyphens
HEADWORD_RE = re.compile(r'^[A-Z][A-Z -]*$')

# POS lines like:
#   Cat, n. Etym: [...]
#   Cat, v. t. [imp. ...] (Naut.)
#   Long"bow`, n. (Zoöl.)
#
# We don't try to fully parse pronunciation; we keep the whole header line.
POS_LINE_RE = re.compile(r'^[A-Z][A-Za-z-]*,')  # "Cat," "Dog," etc.

# Extract "Etym:" anywhere in a line
ETYMO_SPLIT_RE = re.compile(r'\bEtym:\s*', re.IGNORECASE)

# Numbered sense line: "1." or "2. (Naut.)"
SENSE_RE = re.compile(r'^(\d+)\.\s*(?:\(([^)]+)\))?\s*$')

# Sub-sense marker: "(a) ..." "(b) ..." "(c) ..."
SUBSENSE_RE = re.compile(r'^\(([a-z])\)\s*(.*)$')

# Definition and Note starters
DEFN_RE = re.compile(r'^Defn:\s*(.*)$')
NOTE_RE = re.compile(r'^Note:\s*(.*)$')

# Very basic "See ..." extractor (keeps strings; doesn't try to resolve)
SEE_RE = re.compile(r'\bSee\s+([^.;]+)', re.IGNORECASE)

# If you want to tighten domains, you can expand this later.
def normalize_whitespace(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def iter_entries(lines: Iterator[str]) -> Iterator[List[str]]:
    """
    Yield blocks of lines corresponding to one GCIDE headword entry.
    """
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


def ensure_current_entry(current: Optional[Dict]) -> Dict:
    if current is None:
        return {
            "header": None,        # original POS/pronunciation line (best effort)
            "pos": None,           # e.g., "n.", "v. t.", "a."
            "domain": None,        # e.g., "Naut." if present on header line
            "etymology": None,     # if present
            "senses": []           # list of senses
        }
    return current


def ensure_current_sense(current: Dict, current_sense: Optional[Dict]) -> Dict:
    """
    Ensure there is a current sense. If none exists, create implicit sense 1.
    This fixes entries that have Defn: but no "1." (common for verbs).
    """
    if current_sense is None:
        current_sense = {
            "sense": 1,
            "domain": None,
            "definition": "",
            "notes": [],
            "see_also": [],
            "sub_senses": []  # list of {"label": "a", "definition": "...", "notes": [...], "see_also": [...]}
        }
        current["senses"].append(current_sense)
    return current_sense


def parse_pos_line(line: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Best-effort POS extraction from a POS/pronunciation line.

    Examples:
      "Cat, n. Etym: [...]" -> "n."
      "Cat, v. t. [imp....] (Naut.)" -> "v. t."
    """
    # Split at comma and take the rest
    parts = line.split(",", 1)
    if len(parts) != 2:
        return None, None

    rest = parts[1].strip()

    # If Etym: exists, ignore everything after it for POS detection
    rest_no_etym = ETYMO_SPLIT_RE.split(rest)[0].strip()

    # Strip bracketed grammar bits for POS detection (keep header elsewhere)
    rest_no_brackets = re.sub(r'\[[^\]]*\]', '', rest_no_etym).strip()

    # Extract domain in parentheses at end (e.g. "(Naut.)")
    domain = None
    m_dom = re.search(r'\(([^)]+)\)\s*$', rest_no_brackets)
    if m_dom:
        domain = m_dom.group(1).strip()
        rest_no_brackets = re.sub(r'\([^)]+\)\s*$', '', rest_no_brackets).strip()

    # POS is whatever remains (often "n." or "v. t." or "a.")
    pos = rest_no_brackets.strip() if rest_no_brackets else None
    return pos, domain


def extract_etymology_from_line(line: str) -> Optional[str]:
    """
    Extract etymology if it appears inline (e.g. "Cat, n. Etym: [....]").
    Returns the substring after 'Etym:'.
    """
    split = ETYMO_SPLIT_RE.split(line, maxsplit=1)
    if len(split) == 2:
        return normalize_whitespace(split[1])
    return None


def extract_see_also(text: str) -> List[str]:
    """
    Basic 'See X, Y' extraction.
    Returns raw strings (lowercased) split on commas/and.
    """
    out: List[str] = []
    for m in SEE_RE.finditer(text):
        chunk = m.group(1)
        # split on commas and "and"
        chunk = chunk.replace(" and ", ",")
        parts = [p.strip(" ,") for p in chunk.split(",")]
        for p in parts:
            p = normalize_whitespace(p)
            if p:
                out.append(p.lower())
    return out


def append_to_definition(target: Dict, text: str) -> None:
    """
    Append text to a sense definition with spacing.
    """
    text = normalize_whitespace(text)
    if not text:
        return
    if target["definition"]:
        target["definition"] += " " + text
    else:
        target["definition"] = text


def append_to_subsense(sub: Dict, text: str) -> None:
    text = normalize_whitespace(text)
    if not text:
        return
    if sub["definition"]:
        sub["definition"] += " " + text
    else:
        sub["definition"] = text


def parse_entry(entry_lines: List[str]) -> Tuple[str, List[Dict]]:
    """
    Parse one GCIDE entry (one headword, possibly multiple POS blocks).
    Output: headword, list of POS entries
    """
    headword = entry_lines[0].strip().lower()

    entries: List[Dict] = []
    current: Optional[Dict] = None
    current_sense: Optional[Dict] = None
    current_subsense: Optional[Dict] = None

    for raw_line in entry_lines[1:]:
        line = raw_line.rstrip()
        if not line.strip():
            continue

        # Start of a new POS/pronunciation line
        # We treat any line like "Cat, n." / "Long\"bow`, n. (Zoöl.)" as a new entry header
        if POS_LINE_RE.match(line):
            if current is not None:
                entries.append(current)

            current = {
                "header": line.strip(),
                "pos": None,
                "domain": None,
                "etymology": None,
                "senses": []
            }
            current_sense = None
            current_subsense = None

            pos, dom = parse_pos_line(line)
            current["pos"] = pos
            current["domain"] = dom

            ety = extract_etymology_from_line(line)
            if ety:
                current["etymology"] = ety

            continue

        # Etymology on its own line
        if line.startswith("Etym:"):
            current = ensure_current_entry(current)
            current["etymology"] = normalize_whitespace(line.replace("Etym:", "", 1))
            continue

        # Numbered sense line
        m_sense = SENSE_RE.match(line)
        if m_sense:
            current = ensure_current_entry(current)
            current_sense = {
                "sense": int(m_sense.group(1)),
                "domain": (m_sense.group(2).strip() if m_sense.group(2) else None),
                "definition": "",
                "notes": [],
                "see_also": [],
                "sub_senses": []
            }
            current["senses"].append(current_sense)
            current_subsense = None
            continue

        # Sub-sense line like "(a) ..."
        m_sub = SUBSENSE_RE.match(line)
        if m_sub:
            current = ensure_current_entry(current)
            current_sense = ensure_current_sense(current, current_sense)

            label = m_sub.group(1)
            rest = m_sub.group(2)

            sub = {
                "label": label,
                "definition": "",
                "notes": [],
                "see_also": []
            }
            current_sense["sub_senses"].append(sub)
            current_subsense = sub

            # If there's text after (a), treat it as definition content
            if rest.strip():
                append_to_subsense(current_subsense, rest.strip())
                current_subsense["see_also"].extend(extract_see_also(rest))

            continue

        # Defn: line
        m_def = DEFN_RE.match(line)
        if m_def:
            current = ensure_current_entry(current)
            current_sense = ensure_current_sense(current, current_sense)

            def_text = m_def.group(1).strip()

            if current_subsense is not None:
                append_to_subsense(current_subsense, def_text)
                current_subsense["see_also"].extend(extract_see_also(def_text))
            else:
                append_to_definition(current_sense, def_text)
                current_sense["see_also"].extend(extract_see_also(def_text))

            continue

        # Note: line
        m_note = NOTE_RE.match(line)
        if m_note:
            current = ensure_current_entry(current)
            current_sense = ensure_current_sense(current, current_sense)

            note_text = normalize_whitespace(m_note.group(1))

            # Attach to subsense if we're currently inside one; otherwise to the main sense
            if current_subsense is not None:
                current_subsense["notes"].append(note_text)
                current_subsense["see_also"].extend(extract_see_also(note_text))
            else:
                current_sense["notes"].append(note_text)
                current_sense["see_also"].extend(extract_see_also(note_text))

            continue

        # Continuation line: append to the most relevant current target
        current = ensure_current_entry(current)
        current_sense = ensure_current_sense(current, current_sense)

        # If we are inside a subsense, continuation goes there.
        if current_subsense is not None:
            append_to_subsense(current_subsense, line)
            current_subsense["see_also"].extend(extract_see_also(line))
        else:
            append_to_definition(current_sense, line)
            current_sense["see_also"].extend(extract_see_also(line))

    if current is not None:
        entries.append(current)

    # Light cleanup: dedupe see_also lists, normalize
    for e in entries:
        for s in e.get("senses", []):
            s["see_also"] = sorted(set([x for x in s["see_also"] if x]))
            for sub in s.get("sub_senses", []):
                sub["see_also"] = sorted(set([x for x in sub["see_also"] if x]))

    return headword, entries


def main() -> None:
    src = Path("corpora/GCIDE/GCIDE.txt")
    out = Path("corpora/GCIDE/GCIDE.json")

    gcide: Dict = {
        "meta": {
            "source": "gcide-0.54"
        },
        "entries": {}
    }

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
