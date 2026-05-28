"""
embeddings/embedder.py
----------------------
Wrapper around SentenceTransformers + ChromaDB.
Handles embedding generation and storage/retrieval.
"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import uuid
import json
import threading

class ChunkEmbedder:
    """
    Easy‑to‑use class for embedding chunks and querying them.
    """

    def __init__(
        self,
        collection_name: str = "pdf-rag",
        model_name: str = "all-MiniLM-L6-v2",
        persist_directory: Optional[str] = None,
    ) -> None:
        # Chroma client
        if persist_directory:
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.Client()

        # Embedding function – can be used directly by Chroma
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )
        # Keep the model instance for manual encoding if needed
        self.model = SentenceTransformer(model_name)

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
        )
        self._lock = threading.Lock()

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        with self._lock:
            texts = [c["text"] for c in chunks]
            metadatas = []
            for c in chunks:
                meta = c.get("metadata", {}).copy()
                if "raw" in c and c["raw"] is not None:
                    meta["raw_json"] = json.dumps(c["raw"], ensure_ascii=False)
                meta["chunk_id"] = c["id"]  # add unique ID to metadata
                metadatas.append(meta)
            ids = [c.get("id", str(uuid.uuid4())) for c in chunks]
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids,
            )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Manually embed a list of texts (returns list of float lists)."""
        return self.model.encode(texts, show_progress_bar=False).tolist()

    def query(
        self, query: str, top_k: int = 5, where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for chunks similar to *query*.

        Returns
        -------
        dict with keys: "ids", "documents", "metadatas", "distances"
        """
        with self._lock:
            return self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where,  # optional metadata filter, e.g., {"page": 1}
            )

    def delete_by_filter(self, where: Dict[str, Any]) -> None:
        """
        Delete entries from the collection based on metadata filter.
        Example: delete_by_filter({"doc_id": {"$eq": "doc_123"}})
        """
        with self._lock:
            self.collection.delete(where=where)

    def reset(self) -> None:
        """
        Completely reset the collection by deleting and recreating it.
        This is more effective than individual deletes for clearing disk space.
        """
        with self._lock:
            try:
                name = self.collection.name
                self.client.delete_collection(name)
                self.collection = self.client.create_collection(
                    name=name,
                    embedding_function=self.embedding_fn,
                )
            except Exception as e:
                print(f"Error resetting collection: {e}")