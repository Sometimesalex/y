from pathlib import Path

PROLOG_FILE = Path("prolog/wn_g.pl")

def load_glosses():
    print(f"Looking for: {PROLOG_FILE.resolve()}")
    if not PROLOG_FILE.exists():
        print("❌ File does not exist!")
        return {}

    print("✅ File found. Showing first few lines:")
    with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            print(f"LINE {i+1}: {repr(line)}")
            if i > 10:
                break
    return {}
