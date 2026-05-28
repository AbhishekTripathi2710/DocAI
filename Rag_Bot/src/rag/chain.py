"""
rag/chain.py
------------
Retrieval‑augmented generation loop with OpenAI (or Ollama).
"""

import os
import json
from typing import List, Dict, Any, Optional

from openai import OpenAI

# pyrefly: ignore [missing-import]
from embeddings.embedder import ChunkEmbedder
# pyrefly: ignore [missing-import]
from extraction.bm25_index import BM25Index
# pyrefly: ignore [missing-import]
from extraction.hybrid_retriever import HybridRetriever
# pyrefly: ignore [missing-import]
from rag.prompt import build_prompt

MAX_CONTEXT_CHARS = 16000   # ~4000 tokens


class RAGChain:
    def __init__(
        self,
        embedder: ChunkEmbedder,
        bm25_index: Optional[BM25Index] = None,
        groq_api_key: str = "",
        groq_base_url: str = "https://api.groq.com/openai/v1",
        groq_model: str = "llama3-70b-8192",
        ollama_base_url: str = "http://localhost:11434/v1",
        ollama_model: str = "llama3",
        ollama_generation_model: Optional[str] = None,
    ):
        self.embedder = embedder
        self.hybrid_retriever = HybridRetriever(embedder, bm25_index) if bm25_index else None
        
        # Models
        self.groq_model = groq_model
        self.ollama_model = ollama_model
        self.ollama_generation_model = ollama_generation_model or ollama_model
        
        # Clients
        self.groq_client = OpenAI(api_key=groq_api_key, base_url=groq_base_url) if groq_api_key else None
        self.ollama_client = OpenAI(api_key="ollama", base_url=ollama_base_url)

        # Initialize Query Transformation Layer
        # pyrefly: ignore [missing-import]
        from rag.query_transform import QueryRewriter
        self.rewriter = QueryRewriter(
            groq_client=self.groq_client,
            groq_model=self.groq_model,
            ollama_client=self.ollama_client,
            ollama_model=self.ollama_model,
        )

    def answer(
        self,
        question: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        llm_provider: str = "ollama",
    ) -> str:
        """Dense‑only extraction + generation."""
        results = self.embedder.query(question, top_k=top_k, where=where)
        retrieved = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            retrieved.append({"text": doc, "metadata": meta, "type": meta.get("type", "text_block")})
        return self._generate(question, retrieved, llm_provider=llm_provider)

    def _resolve_doc_id(self, filename: str) -> Optional[str]:
        """Resolve a filename (e.g. 'demo-invoice-no-tax-1.pdf') to its doc_id."""
        if not filename:
            return None
            
        # pyrefly: ignore [missing-import]
        from api.config import METADATA_STORE_PATH
        
        try:
            if os.path.exists(METADATA_STORE_PATH):
                with open(METADATA_STORE_PATH, "r") as f:
                    metadata = json.load(f)
                
                fn_lower = filename.lower()
                for doc_id, meta in metadata.items():
                    meta_fn = meta.get("file_name", "").lower()
                    if fn_lower in meta_fn or meta_fn in fn_lower:
                        return doc_id
        except Exception as e:
            print(f"Error resolving doc_id for filename '{filename}': {e}")
            
        return None

    def answer_hybrid(
        self,
        question: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        dense_weight: float = 0.5,
        llm_provider: str = "ollama",
    ) -> str:
        """Hybrid (dense + BM25) extraction + generation with Query Transformation Layer."""
        if not self.hybrid_retriever:
            raise ValueError("BM25 index is not provided. Use answer() for dense only.")
        
        # 1. Route the query using QueryRouter
        route = self.rewriter.route_query(question, llm_provider=llm_provider)
        print(f"\n[Query Transformation Layer] Question: '{question}' routed to: {route}")
        
        retrieved = []
        
        if route == "COMPLEX":
            # Decompose query
            subqueries = self.rewriter.decompose_query(question, llm_provider=llm_provider)
            print(f"[Query Transformation Layer] Decomposed subqueries: {subqueries}")
            
            for sq in subqueries:
                sub_q = sq["query"]
                sub_doc = sq.get("document")
                sub_where = where
                
                # Setup specific where filter for this subquery if targeting a document
                if sub_doc:
                    resolved_id = self._resolve_doc_id(sub_doc)
                    if resolved_id:
                        if where and "doc_id" in where:
                            allowed_ids = []
                            if "$in" in where["doc_id"]:
                                allowed_ids = where["doc_id"]["$in"]
                            elif "$eq" in where["doc_id"]:
                                allowed_ids = [where["doc_id"]["$eq"]]
                                
                            if resolved_id in allowed_ids:
                                sub_where = {"doc_id": {"$eq": resolved_id}}
                        else:
                            sub_where = {"doc_id": {"$eq": resolved_id}}
                
                sub_chunks = self.hybrid_retriever.retrieve(
                    sub_q,
                    top_k=max(2, top_k // 2),
                    where=sub_where,
                    dense_weight=dense_weight
                )
                retrieved.extend(sub_chunks)
                
        elif route == "STANDARD":
            # Expand query
            variations = self.rewriter.expand_query(question, llm_provider=llm_provider)
            print(f"[Query Transformation Layer] Expanded query variations: {variations}")
            
            for var in variations:
                sub_chunks = self.hybrid_retriever.retrieve(
                    var,
                    top_k=top_k,
                    where=where,
                    dense_weight=dense_weight
                )
                retrieved.extend(sub_chunks)
                
        else:  # DIRECT
            retrieved = self.hybrid_retriever.retrieve(
                question,
                top_k=top_k,
                where=where,
                dense_weight=dense_weight
            )
            
        # 2. De-duplicate collected chunks across expansion/decomposition routes
        if route in ("COMPLEX", "STANDARD") and retrieved:
            seen = set()
            unique_chunks = []
            for chunk in retrieved:
                cid = chunk.get("chunk_id")
                if cid not in seen:
                    seen.add(cid)
                    unique_chunks.append(chunk)
            retrieved = unique_chunks[:top_k]
            print(f"[Query Transformation Layer] Retrieved {len(retrieved)} unique chunks after fusion and de-duplication.")

        return self._generate(question, retrieved, llm_provider=llm_provider)

    def _generate(self, question: str, chunks: List[Dict[str, Any]], llm_provider: str = "ollama") -> str:
        # pyrefly: ignore [missing-import]
        from rag.prompt import SYSTEM_INSTRUCTIONS, format_context
        # pyrefly: ignore [missing-import]
        from api.config import MAX_CONTEXT_CHARS
        
        context = format_context(chunks)
        user_content = f"Context:\n{context}\n\nQuestion: {question}"
        
        # Truncate if too long to fit in model window
        if len(user_content) > MAX_CONTEXT_CHARS:
            user_content = user_content[:MAX_CONTEXT_CHARS] + "\n...[context truncated]"
        
        # Select client and model
        if llm_provider == "groq":
            if not self.groq_client:
                return "Groq API key not configured. Please use Ollama or add GROQ_API_KEY to .env"
            client = self.groq_client
            model = self.groq_model
        else:
            client = self.ollama_client
            model = self.ollama_generation_model
        
        print(f"Generating answer using {llm_provider} (model: {model})...")

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.0,
                max_tokens=1500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM error ({llm_provider}): {e}")
            return f"I encountered an error while generating the answer using {llm_provider}. Please try again."