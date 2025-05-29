## 2025-05-28

- Noted that the current semantic ingest process does not deduplicate vector store entries. Re-ingesting the same sessions will create duplicate chunks in ChromaDB, as each ingest uses a new UUID for each chunk.
- This is not a problem for early testing, but could cause bloat and duplicate search results at scale.
- **Reminder:** Before production use or ingesting real data, revisit the vector store ingestion logic. Implement deduplication (e.g., deterministic IDs or upsert logic) and/or periodic cleanup to ensure long-term stability and efficient storage.
- Set a timer to review this in 2 weeks or before the first real data import, whichever comes first. 