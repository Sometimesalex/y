# -------- Grammar / function-word bridge --------

GRAMMAR = {
    "ye": ["you"],
    "thee": ["you"],
    "thou": ["you"],
    "thy": ["your"],
}

# -------- Semantic drift (archaic meaning changes) --------

SEMANTIC = {
    "conversation": ["conduct", "behavior"],
    "prevent": ["precede"],
    "quick": ["living"],
    "meat": ["food"],
    "let": ["hinder"],
    "charity": ["love"],
    "ghost": ["spirit"],
    "peradventure": ["perhaps"],
}

# -------- Archaic verb forms --------

MORPH = {
    "wist": ["knew"],
    "spake": ["spoke"],
    "begat": ["fathered"],
}

def normalize_archaic(tokens):
    """
    Add modern equivalents alongside archaic tokens.
    Original tokens are preserved.
    """
    out = list(tokens)

    for t in tokens:
        if t in GRAMMAR:
            out.extend(GRAMMAR[t])

        if t in SEMANTIC:
            out.extend(SEMANTIC[t])

        if t in MORPH:
            out.extend(MORPH[t])

    return out
