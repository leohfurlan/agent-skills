#!/usr/bin/env python3
"""Compact one-line-per-event view of `silvia events <id> --json` output.

Usage (POSIX shell):
    silvia events <SESSION-UUID> --json | python parse_events.py [contains]

Optional arg: substring filter applied to the rendered line (case-insensitive).
Windows note: run with `python -X utf8` if output hits non-ASCII text.
"""
import json
import sys

raw = sys.stdin.read()
# silvia --json can prefix non-JSON banner lines; find the first array/object
start = min((i for i in (raw.find("["), raw.find("{")) if i != -1), default=-1)
if start == -1:
    print("no JSON found in stdin", file=sys.stderr)
    sys.exit(1)
events = json.loads(raw[start:])
if isinstance(events, dict):
    events = events.get("events", [events])

needle = sys.argv[1].lower() if len(sys.argv) > 1 else None
for e in events:
    p = e.get("payload", {}) or {}
    text = (
        p.get("text")
        or p.get("error")
        or p.get("reason")
        or p.get("detail")
        or p.get("state")
        or ""
    )
    kind = e.get("kind", "?")
    ts = str(e.get("timestamp", ""))[11:19]
    line = f"{e.get('sequence', '?'):>3} {kind:<28} {ts} :: {str(text)[:160]}"
    line = line.replace("\n", " | ")
    if needle and needle not in line.lower():
        continue
    print(line)
