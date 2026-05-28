"""
retrieval/hybrid_retriever.py
-----------------------------
Combines dense (Chroma) and sparse (BM25) retrieval using
Reciprocal Rank Fusion (RRF).

Usage:
    retriever = HybridRetriever(embedder, bm25_index)
    results = retriever.retrieve(query, top_k=5, where=None)
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict

from embeddings.embedder import ChunkEmbedder
from extraction.bm25_index import BM25Index


class HybridRetriever:
    def __init__(self, embedder: ChunkEmbedder, bm25: BM25Index, k_rrf: int = 60):
        self.embedder = embedder
        self.bm25 = bm25
        self.k_rrf = k_rrf  # RRF parameter (tunable, 60 is standard)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        dense_weight: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Returns the top_k chunks (in order) after fusing dense and sparse results.

        Parameters
        ----------
        query : str
        top_k : int
            Number of chunks to return.
        where : dict or None
            Optional metadata filter for the dense retriever.
        dense_weight : float
            Weight of dense scores in the fusion. 0.5 gives equal importance.

        Returns
        -------
        list of chunk dicts (same structure as original chunks).
        """
        # 1. Dense retrieval from Chroma
        search_depth = max(top_k * 3, 30)
        dense_results = self.embedder.collection.query(
            query_texts=[query],
            n_results=search_depth,  # get more to allow fusion
            where=where,
        )
        dense_chunks = []
        for doc, meta in zip(dense_results["documents"][0], dense_results["metadatas"][0]):
            dense_chunks.append({
                "text": doc,
                "metadata": meta,
                "type": meta.get("type", "text_block"),
                "chunk_id": meta.get("chunk_id", doc),   # unique ID stored in metadata
            })

        # 2. Sparse retrieval from BM25
        sparse_hits = self.bm25.search(query, top_k=search_depth)
        sparse_chunks = []
        
        # Apply metadata filtering (where) to BM25 results if needed
        # Since BM25 index search is global, we filter the results manually here
        target_doc_id = None
        target_doc_ids = None
        if where and "doc_id" in where:
            eq_val = where["doc_id"].get("$eq")
            in_val = where["doc_id"].get("$in")
            if eq_val:
                target_doc_id = eq_val
            elif in_val:
                target_doc_ids = set(in_val)

        for idx, score in sparse_hits:
            chunk = self.bm25.chunks[idx]
            
            # Filter by doc_id if specified
            chunk_doc_id = chunk.get("metadata", {}).get("doc_id")
            if target_doc_id and chunk_doc_id != target_doc_id:
                continue
            if target_doc_ids and chunk_doc_id not in target_doc_ids:
                continue

            sparse_chunks.append({
                "text": chunk["text"],
                "metadata": chunk.get("metadata", {}),
                "type": chunk.get("metadata", {}).get("type", "text_block"),
                "score_sparse": score,
                "chunk_id": chunk.get("id", chunk["text"]),   # unique ID from chunker
            })

        # 3. Reciprocal Rank Fusion (RRF)
        # Ranks – order in which they were retrieved (Chroma returns in similarity order; BM25 returns in score order)
        dense_ranks = {i: rank + 1 for rank, i in enumerate(range(len(dense_chunks)))}
        sparse_ranks = {i: rank + 1 for rank, i in enumerate(range(len(sparse_chunks)))}

        fused_scores: Dict[str, float] = defaultdict(float)

        # Add dense contributions
        for i, chunk in enumerate(dense_chunks):
            cid = chunk["chunk_id"]
            rrf_score = 1.0 / (self.k_rrf + dense_ranks[i])
            fused_scores[cid] += dense_weight * rrf_score

        # Add sparse contributions
        for i, chunk in enumerate(sparse_chunks):
            cid = chunk["chunk_id"]
            rrf_score = 1.0 / (self.k_rrf + sparse_ranks[i])
            fused_scores[cid] += (1 - dense_weight) * rrf_score

        # Build a unified lookup by chunk_id
        all_chunks: Dict[str, dict] = {}
        for c in dense_chunks + sparse_chunks:
            all_chunks[c["chunk_id"]] = c

        # Sort by fused score
        sorted_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)
        reranked = [all_chunks[cid] for cid in sorted_ids]
        
        # 3. Apply Diversity Filter for Multi-Document Queries
        # This prevents one document from completely crowding out others in the context.
        final_results = []
        target_doc_id = where.get("doc_id") if where else None
        
        if not target_doc_id:
            # Group by source doc_id
            docs_map: Dict[str, List[Dict[str, Any]]] = {}
            for res in reranked:
                sid = res["metadata"].get("doc_id", "default")
                if sid not in docs_map:
                    docs_map[sid] = []
                docs_map[sid].append(res)
            
            # Round-robin selection across documents
            doc_ids_list = list(docs_map.keys())
            idx = 0
            while len(final_results) < top_k and any(docs_map.values()):
                current_doc_id = doc_ids_list[idx % len(doc_ids_list)]
                if docs_map[current_doc_id]:
                    final_results.append(docs_map[current_doc_id].pop(0))
                idx += 1
        else:
            # If a specific doc_id is selected, no diversity filter is needed
            final_results = reranked[:top_k]

        return final_results