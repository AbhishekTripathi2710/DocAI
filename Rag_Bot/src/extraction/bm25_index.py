"""
retrieval/bm25_index.py
-----------------------
Simple BM25 index over chunk texts.
Uses `rank_bm25` (pip install rank-bm25).

Public API:
    BM25Index.build(chunks: List[Dict[str, Any]]) -> None
    BM25Index.search(query: str, top_k: int) -> List[Tuple[int, float]]
"""

import re
import pickle
import os
import threading
from typing import List, Tuple, Dict, Any
import numpy as np
from rank_bm25 import BM25Okapi


def tokenize(text: str) -> List[str]:
    """
    Robust tokenization: lowercase and split by non-alphanumeric.
    This ensures '09/09/2023,' matches '09/09/2023'.
    """
    if not text:
        return []
    # Lowercase and find all word-like tokens (including dates with / or -)
    # We allow / and - inside tokens to keep dates intact
    tokens = re.findall(r'[a-z0-9/-]+', text.lower())
    return tokens


class BM25Index:
    def __init__(self):
        self.model = None
        self.corpus = []
        self.chunks = []  # keep original chunk dicts for later use
        self._lock = threading.Lock()

    def build(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Build BM25 index from chunk data.
        Each chunk is a dict with "text" and other metadata.
        """
        with self._lock:
            self.chunks = chunks
            self.corpus = [c["text"] for c in chunks]
            tokenized_corpus = [tokenize(doc) for doc in self.corpus]
            
            if tokenized_corpus:
                self.model = BM25Okapi(tokenized_corpus)
            else:
                self.model = None

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        """Return list of (chunk_index, bm25_score)."""
        with self._lock:
            if not self.model or not self.corpus:
                return []
                
            tokenized_query = tokenize(query)
            if not tokenized_query:
                return []
                
            scores = self.model.get_scores(tokenized_query)
            # Return top_k indices with scores
            idxs = np.argsort(scores)[::-1][:top_k]
            return [(int(idx), scores[idx]) for idx in idxs]

    def save(self, path: str) -> None:
        """Save the index to disk using pickle."""
        with self._lock:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                pickle.dump({
                    "chunks": self.chunks,
                    "corpus": self.corpus,
                    "model": self.model
                }, f)

    def load(self, path: str) -> None:
        """Load the index from disk."""
        if not os.path.exists(path):
            return
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
                self.chunks = data.get("chunks", [])
                self.corpus = data.get("corpus", [])
                self.model = data.get("model")
        except Exception:
            # If load fails, we'll just have an empty index that needs rebuilding
            self.chunks = []
            self.corpus = []
            self.model = None