import chromadb
from chromadb.config import Settings
from app import config

if config.CHROMA_PERSIST:
    client = chromadb.Client(Settings(is_persistent=True, persist_directory=config.CHROMA_DIR))
else:
    client = chromadb.Client(Settings(is_persistent=False))

kb = client.get_or_create_collection(name=config.KB_COLLECTION, metadata={"hnsw:space": "cosine"})

def add(ids, documents, metadatas, embeddings):
    return kb.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

def query(query_embedding, n_results: int, where: dict):
    return kb.query(query_embeddings=[query_embedding], n_results=n_results, where=where)

def get(where: dict):
    return kb.get(where=where)
