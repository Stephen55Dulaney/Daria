import chromadb

client = chromadb.Client()
collection = client.get_or_create_collection("daria_transcripts")

def add_chunks_to_vector_store(chunks, embeddings, metadatas):
    for chunk, embedding, metadata in zip(chunks, embeddings, metadatas):
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            metadatas=[metadata]
        )

def semantic_search(query_embedding, top_k=5):
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    return results
