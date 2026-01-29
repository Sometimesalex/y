cat > scripts/prolog_reader.py << 'EOF'
from pathlib import Path

PROLOG_FILE = Path("prolog/wn_g.pl")

def load_glosses():
    print("Opening:", PROLOG_FILE.resolve())

    with PROLOG_FILE.open(encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            print("LINE", i+1, ":", line.strip())
            if i >= 10:
                break

    return {}

if __name__ == "__main__":
    load_glosses()
EOF
