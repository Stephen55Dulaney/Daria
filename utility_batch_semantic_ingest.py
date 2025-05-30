import requests
import json
from pathlib import Path

def ingest_transcript(transcript, session_id):
    url = "http://127.0.0.1:5025/api/semantic_ingest"
    payload = {
        "transcript": transcript,
        "metadata": {"session_id": session_id}
    }
    print(f"Ingesting session {session_id}...")
    response = requests.post(url, json=payload)
    print(f"Session {session_id}: {response.status_code} {response.text}")
    print(f"Finished session {session_id}")

if __name__ == "__main__":
    SESSIONS_DIR = Path("data/interviews/sessions")
    for session_file in SESSIONS_DIR.glob("*.json"):
        session_id = session_file.stem
        with open(session_file) as f:
            session_data = json.load(f)
            # Adjust this line if your transcript is stored differently
            transcript = session_data.get("transcript")
            if not transcript:
                # If transcript is a list of messages, join them
                messages = session_data.get("messages")
                if messages and isinstance(messages, list):
                    transcript = " ".join(m.get("content", "") for m in messages)
            if transcript:
                ingest_transcript(transcript, session_id)
            else:
                print(f"Session {session_id} has no transcript or messages.")