from transcript_processor import TranscriptProcessor

processor = TranscriptProcessor()
collection = processor.collection

# Get all metadatas
all_metadatas = collection.get(include=['metadatas'])['metadatas']

# Extract unique session_ids
session_ids = set()
for meta in all_metadatas:
    if isinstance(meta, dict) and 'session_id' in meta:
        session_ids.add(meta['session_id'])

print(f"Total unique ingested session_ids: {len(session_ids)}")
print("Session IDs:", session_ids)
