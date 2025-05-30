import os
import json
from pathlib import Path

SESSIONS_DIR = Path("data/interviews/sessions")
GUIDES_DIR = Path("data/interviews")

# 1. Delete empty session files and collect valid session IDs
valid_session_ids = set()
for session_file in SESSIONS_DIR.glob("*.json"):
    if session_file.stat().st_size == 0:
        print(f"Deleting empty session: {session_file.name}")
        session_file.unlink()
    else:
        valid_session_ids.add(session_file.stem)

# 2. Update discussion guide files
for guide_file in GUIDES_DIR.glob("*.json"):
    try:
        with open(guide_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Skipping {guide_file.name}: {e}")
        continue
    if "sessions" in data and isinstance(data["sessions"], list):
        original = set(data["sessions"])
        cleaned = [sid for sid in data["sessions"] if sid in valid_session_ids]
        if len(cleaned) != len(data["sessions"]):
            print(f"Updating {guide_file.name}: removed {original - set(cleaned)}")
            data["sessions"] = cleaned
            with open(guide_file, "w") as f:
                json.dump(data, f, indent=2)
