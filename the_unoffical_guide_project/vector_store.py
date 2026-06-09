"""Milestone 4 — Embedding + Vector Store + Retrieval for The Unofficial Guide.

Per the planning.md architecture diagram:
    RecursiveCharacterTextSplitter (800/150)
      -> Sentence-Transformers all-MiniLM-L6-v2
      -> ChromaDB vector store (cosine similarity)
      -> Top-K retrieval (K = 4)

This module loads the chunks produced by the ingestion pipeline (pipeline.py
persists each source to documents/), embeds them with all-MiniLM-L6-v2, and
stores them in a persistent ChromaDB collection tagged with source metadata.
`retrieve()` vectorizes a query with the same model and returns the top-K
most similar chunks via cosine search.
"""

import os
import glob

import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Reuse the ingestion pipeline's chunk spec + documents location so the two
# milestones never drift apart.
from pipeline import CHUNK_SIZE, CHUNK_OVERLAP, DOCUMENTS_DIR

# ==========================================
# CONFIGURATION (from planning.md)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")  # gitignored local vector store
COLLECTION_NAME = "howard_guide"
EMBED_MODEL = "all-MiniLM-L6-v2"
TOP_K = 4

# One shared embedding function so indexing AND query vectorization use the
# exact same model (the "all-MiniLM-L6-v2 Engine" in the diagram).
_embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)


def _source_number(path: str) -> int:
    """Sort key so sources order 1..12 numerically instead of alphabetically."""
    head = os.path.basename(path).split("_", 1)[0]
    return int(head) if head.isdigit() else 999


def load_chunks():
    """Reload the ingestion pipeline's persisted corpus (documents/*.txt) and
    re-chunk it with the pipeline's splitter settings.

    Returns a list of (chunk_id, text, metadata) tuples.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    records = []
    for path in sorted(glob.glob(os.path.join(DOCUMENTS_DIR, "*.txt")), key=_source_number):
        text = open(path, encoding="utf-8").read()
        if not text.strip():
            continue
        source = os.path.splitext(os.path.basename(path))[0]
        for i, doc in enumerate(splitter.create_documents([text])):
            records.append((f"{source}__chunk_{i}", doc.page_content, {"source_origin": source}))
    return records


def build_vector_store(reset: bool = True):
    """Embed every chunk with all-MiniLM-L6-v2 and store it in ChromaDB using
    cosine similarity, tagged with its source. Returns the collection."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass  # collection didn't exist yet

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embed_fn,
        metadata={"hnsw:space": "cosine"},  # cosine similarity per the diagram
    )

    records = load_chunks()
    if not records:
        raise RuntimeError("No chunks found. Run pipeline.py first to populate documents/.")

    collection.add(
        ids=[r[0] for r in records],
        documents=[r[1] for r in records],
        metadatas=[r[2] for r in records],
    )

    print(f"Indexed {collection.count()} chunks into '{COLLECTION_NAME}' "
          f"(cosine, {EMBED_MODEL}).")
    return collection


def get_collection():
    """Open the existing persistent collection for querying."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(name=COLLECTION_NAME, embedding_function=_embed_fn)


def retrieve(query: str, k: int = TOP_K):
    """Vectorize the query with all-MiniLM-L6-v2 and return the top-k most
    similar chunks via cosine search.

    Returns a list of dicts: {rank, source_origin, similarity, text}.
    """
    collection = get_collection()
    res = collection.query(query_texts=[query], n_results=k)

    hits = []
    for rank, (doc, meta, dist) in enumerate(
        zip(res["documents"][0], res["metadatas"][0], res["distances"][0]), start=1
    ):
        hits.append({
            "rank": rank,
            "source_origin": meta.get("source_origin"),
            "similarity": round(1.0 - dist, 4),  # cosine distance -> similarity
            "text": doc,
        })
    return hits


if __name__ == "__main__":
    print("=== Building vector store ===")
    build_vector_store(reset=True)

    print("\n=== Retrieval smoke test (K = 4) ===")
    demo_query = "How do I clear a financial hold on my account?"
    print(f"Query: {demo_query}\n")
    for h in retrieve(demo_query):
        snippet = h["text"][:220].replace("\n", " ")
        print(f"[{h['rank']}] source={h['source_origin']} | cosine_sim={h['similarity']}")
        print(f"    {snippet}...\n")
