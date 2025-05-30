import requests

API_URL = "http://127.0.0.1:5025"

def get_sessions():
    resp = requests.get(f"{API_URL}/api/sessions")
    resp.raise_for_status()
    return resp.json()

def ingest_session(session):
    transcript = session.get("transcript", "")
    if not transcript.strip():
        print(f"Skipping session {session['id']} (no transcript)")
        return False
    metadata = {k: v for k, v in session.items() if k not in ("transcript", "messages") and v is not None}
    resp = requests.post(f"{API_URL}/api/semantic_ingest", json={
        "transcript": transcript,
        "metadata": metadata
    })
    if resp.ok:
        print(f"Semantic ingest OK for {session['id']}")
        return True
    else:
        print(f"Semantic ingest FAILED for {session['id']}: {resp.text}")
        return False

def analyze_session(session_id):
    # Try both endpoints, depending on your API
    for endpoint in [
        f"/api/session/{session_id}/analyze",
        f"/api/research_session/{session_id}/analyze"
    ]:
        url = API_URL + endpoint
        try:
            resp = requests.post(url)
            if resp.ok:
                print(f"Analysis OK for {session_id}")
                return True
        except Exception as e:
            print(f"Error analyzing {session_id} at {endpoint}: {e}")
    print(f"Analysis FAILED for {session_id}")
    return False

def main():
    sessions = get_sessions()
    print(f"Found {len(sessions)} sessions")
    for session in sessions:
        sid = session.get("id")
        print(f"\nProcessing session: {sid}")
        ingested = ingest_session(session)
        if ingested:
            analyze_session(sid)

if __name__ == "__main__":
    main()
