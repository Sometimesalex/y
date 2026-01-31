ARCHAIC = {
    "conversation": ["conduct", "behavior"],
    "prevent": ["precede"],
    "quick": ["living"],
    "meat": ["food"],
    "let": ["hinder"],
    "charity": ["love"],
    "ghost": ["spirit"],
    "peradventure": ["perhaps"],
    "wist": ["knew"],
    "spake": ["spoke"],
    "begat": ["fathered"],
    "ye": ["you"],
    "thee": ["you"],
    "thou": ["you"],
    "thy": ["your"],
}

def normalize_archaic(tokens):
    out = list(tokens)
    for t in tokens:
        if t in ARCHAIC:
            out.extend(ARCHAIC[t])
    return out
