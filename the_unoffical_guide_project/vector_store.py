"""Milestone 4 — Embedding + Vector Store + Retrieval for The Unofficial Guide.

Per the planning.md architecture diagram:
    RecursiveCharacterTextSplitter (800/150)
      -> Sentence-Transformers all-MiniLM-L6-v2
      -> ChromaDB vector store (cosine similarity)
      -> Top-K retrieval (K = 4)

Loads persisted documents from documents/ (including crawled PDF forms),
embeds them with all-MiniLM-L6-v2, stores them in persistent ChromaDB,
and executes cosine similarity retrieval with rich citation metadata.
"""

import os
import glob
import re

import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

from pipeline import CHUNK_SIZE, CHUNK_OVERLAP, DOCUMENTS_DIR, SOURCES

# ==========================================
# CONFIGURATION (from planning.md)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "howard_guide"
EMBED_MODEL = "all-MiniLM-L6-v2"
TOP_K = 4

_embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)


def _source_number(path: str) -> int:
    """Sort key so sources order 1..12 numerically instead of alphabetically."""
    base = os.path.basename(path)
    head = base.split("_", 1)[0]
    return int(head) if head.isdigit() else 999


def _infer_metadata_from_filename(filename: str) -> dict:
    """Extracts source origin, document type, and parent URLs from the document name."""
    stem = os.path.splitext(filename)[0]

    # Check if this file was created by the PDF crawler (e.g., 10_registrar_forms_form_Graduation_Application)
    if "_form_" in stem:
        source_key, form_title = stem.split("_form_", 1)
        cleaned_title = form_title.replace("_", " ").strip()
        parent_url = SOURCES.get(source_key, "")
        return {
            "source_origin": source_key,
            "title": cleaned_title,
            "parent_page": parent_url,
            "url": parent_url,
            "type": "linked_pdf_form"
        }

    # Standard source files (e.g., 2_hu_administration.txt)
    matched_url = SOURCES.get(stem, "")
    return {
        "source_origin": stem,
        "title": stem,
        "parent_page": matched_url,
        "url": matched_url,
        "type": "base_corpus"
    }


def load_chunks():
    """Reloads documents/*.txt (including crawled PDF forms) and chunks them.

    Returns a list of (chunk_id, text, metadata) tuples.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    records = []
    files = sorted(glob.glob(os.path.join(DOCUMENTS_DIR, "*.txt")), key=_source_number)

    for path in files:
        filename = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip():
            continue

        base_meta = _infer_metadata_from_filename(filename)
        stem = os.path.splitext(filename)[0]

        for i, doc in enumerate(splitter.create_documents([text])):
            chunk_meta = {**base_meta, "chunk_index": i}
            records.append((f"{stem}__chunk_{i}", doc.page_content, chunk_meta))

    return records


def build_vector_store(reset: bool = True):
    """Embeds chunks with all-MiniLM-L6-v2 and writes to ChromaDB with cosine similarity."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

    records = load_chunks()
    if not records:
        raise RuntimeError("No chunks found. Run pipeline.py first to populate documents/.")

    # Ingest in batches to prevent payload bottlenecks
    batch_size = 100
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        collection.add(
            ids=[r[0] for r in batch],
            documents=[r[1] for r in batch],
            metadatas=[r[2] for r in batch],
        )

    print(f"Indexed {collection.count()} chunks into '{COLLECTION_NAME}' (cosine, {EMBED_MODEL}).")
    return collection


def get_collection():
    """Opens the existing persistent collection for querying."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(name=COLLECTION_NAME, embedding_function=_embed_fn)


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """Retrieves top-k most similar chunks via cosine distance search.

    Returns a list of dicts: {rank, source_origin, title, url, type, similarity, text}.
    """
    collection = get_collection()
    res = collection.query(query_texts=[query], n_results=k)

    hits = []
    if not res["documents"] or not res["documents"][0]:
        return hits

    for rank, (doc, meta, dist) in enumerate(
        zip(res["documents"][0], res["metadatas"][0], res["distances"][0]), start=1
    ):
        hits.append({
            "rank": rank,
            "source_origin": meta.get("source_origin"),
            "title": meta.get("title"),
            "url": meta.get("url"),
            "type": meta.get("type"),
            "similarity": round(1.0 - dist, 4),  # Cosine distance to similarity score
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
        print(f"[{h['rank']}] source={h['source_origin']} | type={h['type']} | similarity={h['similarity']}")
        if h.get("url"):
            print(f"    URL: {h['url']}")
        print(f"    Snippet: {snippet}...\n")