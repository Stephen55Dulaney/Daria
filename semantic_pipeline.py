# semantic_pipeline.py
import openai
import tiktoken
import chromadb
import json
import os

# Tagging schema for LLM and frontend reference
TAGGING_SCHEMA = {
    "themes": ["navigation", "workflow", "terminology", "system status", "error handling"],
    "emotions": ["frustration", "confusion", "satisfaction", "neutral", "interest"],
    "intent": ["clarify", "report issue", "describe process", "request help", "feedback"],
    "task_success": ["success", "partial success", "failure", "not attempted", "not applicable"],
    "interaction_modality": ["spoken", "typed", "mixed"],
    "ux_heuristic_violations": [
        "visibility of system status",
        "match between system and real world",
        "error prevention",
        "consistency and standards",
        "user control and freedom"
    ],
    "persona": ["retailer", "distributor", "admin", "other"],
    "goal_satisfaction": ["achieved", "partially achieved", "not achieved", "not applicable"]
}

def chunk_transcript(transcript, max_tokens=256):
    # Simple chunker: split by sentences, group into chunks
    # Replace with your preferred logic
    import re
    sentences = re.split(r'(?<=[.!?]) +', transcript)
    chunks = []
    current = []
    current_tokens = 0
    enc = tiktoken.encoding_for_model("text-embedding-3-large")
    for sent in sentences:
        tokens = len(enc.encode(sent))
        if current_tokens + tokens > max_tokens and current:
            chunks.append(' '.join(current))
            current = []
            current_tokens = 0
        current.append(sent)
        current_tokens += tokens
    if current:
        chunks.append(' '.join(current))
    return chunks

def embed_chunks(chunks):
    client = openai.OpenAI()  # This uses the OPENAI_API_KEY from your environment
    response = client.embeddings.create(input=chunks, model="text-embedding-3-large")
    return [item.embedding for item in response.data]

def tag_chunk(chunk, metadata):
    prompt = f"""
    You are a UX research analyst reviewing a chunk of an interview transcript.

    Your job is to:
    1. Identify any key themes discussed (choose from: {TAGGING_SCHEMA['themes']}).
    2. Identify the emotional tone or emotions (choose from: {TAGGING_SCHEMA['emotions']}).
    3. Suggest a short affinity hint.
    4. Suggest follow-up questions.
    5. Classify the user's intent (choose from: {TAGGING_SCHEMA['intent']}).
    6. Note any signs of frustration, confusion, or cognitive load.
    7. Identify the interaction modality (choose from: {TAGGING_SCHEMA['interaction_modality']}).
    8. Indicate if the user succeeded or failed at their intended task in this chunk (choose from: {TAGGING_SCHEMA['task_success']}).
    9. Tag any UX heuristic violations (choose from: {TAGGING_SCHEMA['ux_heuristic_violations']}).
    10. If available, annotate which test plan phase this chunk belongs to.
    11. Assign a persona/segment (choose from: {TAGGING_SCHEMA['persona']}).
    12. Indicate goal satisfaction (choose from: {TAGGING_SCHEMA['goal_satisfaction']}).
    13. For each pain point, assign a severity score (1=minor, 5=critical) and provide a supporting quote if present.
    14. Tag any quotes in this chunk with their associated theme, emotion, and persona.

    Input chunk:
    ---
    Speaker: {metadata.get('speaker')}
    Timestamp: {metadata.get('timestamp')}
    Phase: {metadata.get('phase')}
    Role: {metadata.get('role')}
    Persona: {metadata.get('persona', '')}
    Transcript Text: "{chunk}"

    Output format:
    {{
      "themes": [...],
      "emotions": [...],
      "affinity_hint": "...",
      "follow_up_questions": [...],
      "intent": "...",
      "frustration_markers": [...],
      "interaction_modality": "...",
      "task_success": "...",
      "ux_heuristic_violations": [...],
      "phase": "{metadata.get('phase', '')}",
      "persona": "{metadata.get('persona', '')}",
      "goal_satisfaction": "...",
      "pain_points": [
        {{
          "issue": "...",
          "frequency": "...",
          "impact": "...",
          "severity_score": 1,
          "sentiment": "...",
          "quote": "..."
        }}
      ],
      "quotes": [
        {{
          "text": "...",
          "theme": "...",
          "emotion": "...",
          "persona": "..."
        }}
      ]
    }}
    """
    client = openai.OpenAI()
    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}]
    )
    return completion.choices[0].message.content

def save_annotations(session_id, annotations):
    ANNOTATIONS_DIR = "/Users/sdulaney/DariaInterviewTool/data/annotations"
    os.makedirs(ANNOTATIONS_DIR, exist_ok=True)
    path = os.path.join(ANNOTATIONS_DIR, f"{session_id}.json")
    with open(path, "w") as f:
        json.dump(annotations, f, indent=2)

if __name__ == "__main__":
    session_id = "your-session-id"
    annotations = []

    with open("path/to/your/p/session_file.json", "r") as f:
        session = json.load(f)

    for msg in session["messages"]:
        semantic_json = tag_chunk(msg["content"], msg)
        try:
            semantic_data = json.loads(semantic_json)
        except Exception:
            semantic_data = {"raw": semantic_json}
        annotation = {
            "id": msg["id"],
            "messageId": msg["id"],
            "content": msg["content"],
            "semantic": semantic_data,
            "user": {"name": "System"},
            "timestamp": msg.get("timestamp", "")
        }
        annotations.append(annotation)

    save_annotations(session_id, annotations)