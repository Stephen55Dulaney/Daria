import chromadb
import uuid

client = chromadb.Client()
collection = client.get_or_create_collection("daria_transcripts")

def add_chunks_to_vector_store(chunks, embeddings, metadatas):
    for chunk, embedding, metadata in zip(chunks, embeddings, metadatas):
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())]
        )

def semantic_search(query_embedding, top_k=10, filters=None):
    query_args = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
    }
    if filters and isinstance(filters, dict) and len(filters) > 0:
        query_args["where"] = filters

    results = collection.query(**query_args)
    return results
