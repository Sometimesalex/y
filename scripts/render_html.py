#!/usr/bin/env python3

import json
from pathlib import Path
from datetime import datetime

# ---- paths (adjust later if needed) ----
ROOT = Path(__file__).resolve().parents[1]
INTERPRETER_OUTPUT = ROOT / "output" / "interpreter_result.json"
WEB_DIR = ROOT / "web"
OUTPUT_HTML = WEB_DIR / "index.html"

print("[render_html] Starting HTML render")
print(f"[render_html] Reading: {INTERPRETER_OUTPUT}")

# ---- sanity checks ----
if not INTERPRETER_OUTPUT.exists():
    raise FileNotFoundError(
        f"Interpreter output not found: {INTERPRETER_OUTPUT}"
    )

WEB_DIR.mkdir(parents=True, exist_ok=True)

# ---- load interpreter result ----
with open(INTERPRETER_OUTPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

print("[render_html] Interpreter data loaded")
print(f"[render_html] Keys: {list(data.keys())}")

# ---- extract fields safely ----
question = data.get("question", "Unknown question")
answer = data.get("answer", "(no answer produced)")
context = data.get("context", [])
timestamp = datetime.utcnow().isoformat() + "Z"

# ---- build HTML ----
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Query Result</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      background: #0b0b0b;
      color: #ffffff;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      line-height: 1.6;
      padding: 24px;
      max-width: 860px;
      margin: auto;
    }}
    h1 {{ font-size: 1.4rem; }}
    h2 {{ font-size: 1.1rem; margin-top: 32px; }}
    .meta {{
      color: #9aa0a6;
      font-size: 0.9rem;
      margin-bottom: 24px;
    }}
    .answer {{
      white-space: pre-wrap;
      background: rgba(255,255,255,0.05);
      padding: 16px;
      border-radius: 12px;
    }}
    ul {{
      margin-top: 12px;
    }}
  </style>
</head>
<body>

<h1>Question</h1>
<div class="answer">{question}</div>

<h2>Answer</h2>
<div class="answer">{answer}</div>

<h2>Context</h2>
<ul>
{''.join(f'<li>{c}</li>' for c in context)}
</ul>

<div class="meta">
Generated at {timestamp}
</div>

</body>
</html>
"""

# ---- write output ----
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print(f"[render_html] Wrote HTML to: {OUTPUT_HTML}")
print("[render_html] Done")
