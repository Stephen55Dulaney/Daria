# semantic_pipeline.py
import openai
import tiktoken

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
    # Call OpenAI LLM for tagging
    prompt = f"""
    You are a UX research analyst reviewing a chunk of an interview transcript.

    Your job is to:
    1. Identify any key themes discussed.
    2. Identify the emotional tone or emotions.
    3. Suggest a short affinity hint.
    4. Suggest follow-up questions.

    Input chunk:
    ---
    Speaker: {metadata.get('speaker')}
    Timestamp: {metadata.get('timestamp')}
    Phase: {metadata.get('phase')}
    Role: {metadata.get('role')}
    Transcript Text: "{chunk}"

    Output format:
    {{
      "themes": [...],
      "emotions": [...],
      "affinity_hint": "...",
      "follow_up_questions": [...]
    }}
    """
    client = openai.OpenAI()
    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}]
    )
    return completion.choices[0].message.content

# Add more as needed