#!/usr/bin/env python3
"""
GCIDE.txt -> GCIDE.json converter (GCIDE 0.54 style)

Fixes added (based on CAT sanity check):
- Multi-line bracketed etymology: collect until closing ']'
- Sense markers can appear mid-line: detect/split '2. (Naut.)' etc anywhere
- Sub-sense markers can appear mid-line: detect/split '(a) ... (b) ...'
- Multi-line Note: blocks: continuation lines stay in notes, not definitions
- Implicit sense 1 for entries with Defn: but no numbered sense
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator

# Headword lines are ALL CAPS, possibly with spaces or hyphens
HEADWORD_RE = re.compile(r'^[A-Z][A-Z -]*$')

# POS/pronunciation header lines start like "Cat," "Long\"bow`," etc.
POS_LINE_RE = re.compile(r'^[A-Z][A-Za-z"\'`-]*,')

# Etymology marker (inline or standalone)
ETYMO_SPLIT_RE = re.compile(r'\bEtym:\s*', re.IGNORECASE)

# Sense markers at start of line
SENSE_LINE_RE = re.compile(r'^(\d+)\.\s*(?:\(([^)]+)\))?\s*$')

# Sense markers anywhere in text (start or preceded by whitespace)
SENSE_ANY_RE = re.compile(r'(?:(?<=\s)|^)(\d+)\.\s*(?:\(([^)]+)\))?')

# Sub-sense marker at start of line
SUBSENSE_LINE_RE = re.compile(r'^\(([a-z])\)\s*(.*)$')

# Sub-sense markers anywhere in text (start or preceded by whitespace)
SUBSENSE_ANY_RE = re.compile(r'(?:(?<=\s)|^)\(([a-z])\)\s*')

# Definition and Note starters
DEFN_RE = re.compile(r'^Defn:\s*(.*)$')
NOTE_RE = re.compile(r'^Note:\s*(.*)$')

# Basic "See ..." extraction
SEE_RE = re.compile(r'\bSee\s+([^.;]+)', re.IGNORECASE)

# Domain tags in header like "(Naut.)" at end
END_PARENS_RE = re.compile(r'\(([^)]+)\)\s*$')


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
        "sub_senses": []  # list of {"label": "a", "definition": "", "notes": [], "see_also": []}
    }


def new_subsense(label: str) -> Dict:
    return {
        "label": label,
        "definition": "",
        "notes": [],
        "see_also": []
    }


def ensure_current_entry(current: Optional[Dict]) -> Dict:
    return current if current is not None else new_pos_block()


def ensure_current_sense(current: Dict, current_sense: Optional[Dict]) -> Dict:
    """
    Ensure there is a current sense. If none exists, create implicit sense 1.
    """
    if current_sense is None:
        current_sense = new_sense(1, None)
        current["senses"].append(current_sense)
    return current_sense


def extract_see_also(text: str) -> List[str]:
    out: List[str] = []
    for m in SEE_RE.finditer(text):
        chunk = m.group(1)
        chunk = chunk.replace(" and ", ",")
        parts = [p.strip(" ,") for p in chunk.split(",")]
        for p in parts:
            p = normalize_whitespace(p)
            if p:
                out.append(p.lower())
    return out


def dedupe_sorted(xs: List[str]) -> List[str]:
    return sorted(set([x for x in xs if x]))


def parse_pos_line(line: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Return (pos, domain, etymology_inline)
    """
    pos = None
    domain = None
    ety = None

    # Inline etymology
    split = ETYMO_SPLIT_RE.split(line, maxsplit=1)
    left = split[0].strip()
    if len(split) == 2:
        ety = split[1].strip()

    # POS is after the comma
    parts = left.split(",", 1)
    if len(parts) == 2:
        rest = parts[1].strip()

        # Strip bracketed grammar for POS detection
        rest = re.sub(r'\[[^\]]*\]', '', rest).strip()

        # Domain in trailing parentheses
        m_dom = END_PARENS_RE.search(rest)
        if m_dom:
            domain = m_dom.group(1).strip()
            rest = END_PARENS_RE.sub("", rest).strip()

        pos = rest if rest else None

    return pos, domain, ety


def append_text(target: Dict, field: str, text: str) -> None:
    text = normalize_whitespace(text)
    if not text:
        return
    if target[field]:
        target[field] += " " + text
    else:
        target[field] = text


def split_inline_senses(text: str) -> List[Tuple[Optional[int], Optional[str], str]]:
    """
    Split a chunk by inline sense markers. Returns a list of segments:
      (sense_number or None, domain or None, segment_text_after_marker_or_plain)
    If a marker appears, that segment starts a new sense.
    """
    text = normalize_whitespace(text)
    if not text:
        return []

    matches = list(SENSE_ANY_RE.finditer(text))
    if not matches:
        return [(None, None, text)]

    segments: List[Tuple[Optional[int], Optional[str], str]] = []
    last = 0

    for m in matches:
        start = m.start()

        # preceding text belongs to current sense
        if start > last:
            pre = normalize_whitespace(text[last:start])
            if pre:
                segments.append((None, None, pre))

        n = int(m.group(1))
        dom = m.group(2).strip() if m.group(2) else None

        # text after marker continues this new sense until next marker
        last = m.end()
        # placeholder; will be filled after we know next marker boundary
        segments.append((n, dom, ""))

    # fill marker segments with trailing text
    # walk segments, assign following text between marker end and next marker start
    # Recompute using match boundaries
    marker_positions = [(m.end(), m.start()) for m in matches]  # (end, start)
    # marker segment indexes in segments list are those with n != None
    seg_idx = 0
    marker_i = 0
    for i, seg in enumerate(segments):
        if seg[0] is not None:
            end = matches[marker_i].end()
            next_start = matches[marker_i + 1].start() if marker_i + 1 < len(matches) else len(text)
            seg_text = normalize_whitespace(text[end:next_start])
            segments[i] = (seg[0], seg[1], seg_text)
            marker_i += 1

    return segments


def apply_inline_subsenses(current_sense: Dict, text: str) -> Tuple[Optional[Dict], str]:
    """
    If text contains inline (a) (b) markers, split into subsenses.
    Returns (current_subsense, leftover_main_text_if_any)
    """
    text = normalize_whitespace(text)
    if not text:
        return None, ""

    matches = list(SUBSENSE_ANY_RE.finditer(text))
    if not matches:
        return None, text

    # Any main text before first (a) belongs to main definition
    first_start = matches[0].start()
    main_prefix = normalize_whitespace(text[:first_start])

    for i, m in enumerate(matches):
        label = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = normalize_whitespace(text[start:end])
        sub = new_subsense(label)
        if chunk:
            append_text(sub, "definition", chunk)
            sub["see_also"].extend(extract_see_also(chunk))
        current_sense["sub_senses"].append(sub)

    # current_subsense is the last one
    current_subsense = current_sense["sub_senses"][-1] if current_sense["sub_senses"] else None
    return current_subsense, main_prefix


def parse_entry(entry_lines: List[str]) -> Tuple[str, List[Dict]]:
    headword = entry_lines[0].strip().lower()

    entries: List[Dict] = []
    current: Optional[Dict] = None
    current_sense: Optional[Dict] = None
    current_subsense: Optional[Dict] = None

    # State for multi-line etymology (bracketed) and notes
    in_etymology = False
    in_note = False
    note_target: Optional[Dict] = None  # either current_sense or current_subsense

    for raw_line in entry_lines[1:]:
        line = raw_line.rstrip()
        if not line.strip():
            # blank line ends note mode (common)
            in_note = False
            note_target = None
            continue

        # POS header line
        if POS_LINE_RE.match(line):
            if current is not None:
                entries.append(current)

            current = new_pos_block(header=line.strip())
            current_sense = None
            current_subsense = None
            in_etymology = False
            in_note = False
            note_target = None

            pos, dom, ety_inline = parse_pos_line(line)
            current["pos"] = pos
            current["domain"] = dom

            if ety_inline:
                # Start etymology capture; may continue across lines until ']'
                current["etymology"] = normalize_whitespace(ety_inline)
                if "]" not in ety_inline:
                    in_etymology = True
                else:
                    in_etymology = False
            continue

        # If we're in multi-line etymology, keep appending until closing ']'
        if in_etymology:
            current = ensure_current_entry(current)
            # append raw line content to etymology
            cur = current.get("etymology") or ""
            add = normalize_whitespace(line)
            current["etymology"] = normalize_whitespace(cur + " " + add) if cur else add
            if "]" in line:
                in_etymology = False
            continue

        # Standalone Etym:
        if line.startswith("Etym:"):
            current = ensure_current_entry(current)
            ety = normalize_whitespace(line.replace("Etym:", "", 1))
            current["etymology"] = ety
            if ety.startswith("[") and "]" not in ety:
                in_etymology = True
            continue

        # If we are in a multi-line Note block and this line isn't a new structural marker, append to note
        if in_note:
            # structural markers that terminate note continuation
            if (POS_LINE_RE.match(line) or SENSE_LINE_RE.match(line) or DEFN_RE.match(line)
                    or NOTE_RE.match(line) or SUBSENSE_LINE_RE.match(line)):
                in_note = False
                note_target = None
            else:
                if note_target is not None and note_target.get("notes"):
                    note_target["notes"][-1] = normalize_whitespace(note_target["notes"][-1] + " " + line.strip())
                    # also extract see_also from continuation
                    note_target["see_also"].extend(extract_see_also(line))
                    continue
                else:
                    in_note = False
                    note_target = None

        # Numbered sense line (pure)
        m_sense_line = SENSE_LINE_RE.match(line)
        if m_sense_line:
            current = ensure_current_entry(current)
            current_sense = new_sense(int(m_sense_line.group(1)),
                                     m_sense_line.group(2).strip() if m_sense_line.group(2) else None)
            current["senses"].append(current_sense)
            current_subsense = None
            continue

        # Sub-sense line (pure)
        m_sub_line = SUBSENSE_LINE_RE.match(line)
        if m_sub_line:
            current = ensure_current_entry(current)
            current_sense = ensure_current_sense(current, current_sense)
            sub = new_subsense(m_sub_line.group(1))
            current_sense["sub_senses"].append(sub)
            current_subsense = sub
            rest = m_sub_line.group(2).strip()
            if rest:
                append_text(current_subsense, "definition", rest)
                current_subsense["see_also"].extend(extract_see_also(rest))
            continue

        # Note line
        m_note = NOTE_RE.match(line)
        if m_note:
            current = ensure_current_entry(current)
            current_sense = ensure_current_sense(current, current_sense)

            note_text = normalize_whitespace(m_note.group(1))
            if current_subsense is not None:
                current_subsense["notes"].append(note_text)
                current_subsense["see_also"].extend(extract_see_also(note_text))
                note_target = current_subsense
            else:
                current_sense["notes"].append(note_text)
                current_sense["see_also"].extend(extract_see_also(note_text))
                note_target = current_sense

            in_note = True
            continue

        # Defn line
        m_def = DEFN_RE.match(line)
        if m_def:
            current = ensure_current_entry(current)
            current_sense = ensure_current_sense(current, current_sense)
            text = normalize_whitespace(m_def.group(1))

            # Split by inline sense markers first (handles " ... 2. (Naut.) ...")
            for sn, dom, seg in split_inline_senses(text):
                if sn is not None:
                    # start new sense
                    current_sense = new_sense(sn, dom)
                    current["senses"].append(current_sense)
                    current_subsense = None
                    # Inline subsenses inside seg
                    current_subsense, main_prefix = apply_inline_subsenses(current_sense, seg)
                    if main_prefix:
                        append_text(current_sense, "definition", main_prefix)
                        current_sense["see_also"].extend(extract_see_also(main_prefix))
                    # If no subsense markers, seg goes to definition
                    if current_subsense is None and seg:
                        append_text(current_sense, "definition", seg)
                        current_sense["see_also"].extend(extract_see_also(seg))
                    continue

                # continuation of current sense/subsense
                if current_subsense is not None:
                    append_text(current_subsense, "definition", seg)
                    current_subsense["see_also"].extend(extract_see_also(seg))
                else:
                    # Inline subsense markers may appear even in continuation
                    new_sub, main_prefix = apply_inline_subsenses(current_sense, seg)
                    if main_prefix:
                        append_text(current_sense, "definition", main_prefix)
                        current_sense["see_also"].extend(extract_see_also(main_prefix))
                    if new_sub is not None:
                        current_subsense = new_sub
                    elif seg:
                        append_text(current_sense, "definition", seg)
                        current_sense["see_also"].extend(extract_see_also(seg))

            continue

        # Continuation line (definition stream) — also split on inline senses and inline subsenses
        current = ensure_current_entry(current)
        current_sense = ensure_current_sense(current, current_sense)

        text = normalize_whitespace(line)

        for sn, dom, seg in split_inline_senses(text):
            if sn is not None:
                current_sense = new_sense(sn, dom)
                current["senses"].append(current_sense)
                current_subsense = None

                current_subsense, main_prefix = apply_inline_subsenses(current_sense, seg)
                if main_prefix:
                    append_text(current_sense, "definition", main_prefix)
                    current_sense["see_also"].extend(extract_see_also(main_prefix))
                if current_subsense is None and seg:
                    append_text(current_sense, "definition", seg)
                    current_sense["see_also"].extend(extract_see_also(seg))
                continue

            # continuation
            if current_subsense is not None:
                append_text(current_subsense, "definition", seg)
                current_subsense["see_also"].extend(extract_see_also(seg))
            else:
                new_sub, main_prefix = apply_inline_subsenses(current_sense, seg)
                if main_prefix:
                    append_text(current_sense, "definition", main_prefix)
                    current_sense["see_also"].extend(extract_see_also(main_prefix))
                if new_sub is not None:
                    current_subsense = new_sub
                elif seg:
                    append_text(current_sense, "definition", seg)
                    current_sense["see_also"].extend(extract_see_also(seg))

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
