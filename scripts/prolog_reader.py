def load_glosses():
    glosses = {}
    pattern = re.compile(r"g\((\d+),\s*'(.*)'\)\.")

    with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            match = pattern.match(line)
            if match:
                synset_id, gloss = match.groups()
                glosses[synset_id] = gloss
            else:
                print("NO MATCH:", line)  # Debugging output

    return glosses
