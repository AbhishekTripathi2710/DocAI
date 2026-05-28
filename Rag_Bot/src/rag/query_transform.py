"""
rag/query_transform.py
-----------------------
Provides query routing, multi-query expansion, and multi-step decomposition.
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

ROUTE_SYSTEM_PROMPT = """You are an advanced query router for a Retrieval-Augmented Generation (RAG) system.
Your job is to analyze the user's question and classify it into one of three categories:

1. COMPLEX: The query requires comparing, aggregating, or combining information across multiple documents, or has multiple distinct parts that should be solved in sequence.
Examples:
- "Compare the invoice numbers of invoice_Steve.pdf and invoice_John.pdf"
- "What is the total sum of tax paid in all invoices?"
- "Which document has the highest amount due, and who is the customer?"

2. STANDARD: The query is an open-ended, semantic, or conceptual question that could benefit from phrasal variations to improve keyword/concept coverage in a search index.
Examples:
- "What is the policy for tax refunds?"
- "How do I claim a refund for late delivery?"
- "What are the payment terms?"

3. DIRECT: The query is a direct look up of a specific fact, a simple question about a single document, or an exact keyword query that does NOT need expansion or decomposition.
Examples:
- "What is the invoice number for invoice_Steve.pdf?"
- "Who is the customer in demo-invoice.pdf?"
- "204869"
- "demo-invoice-no-tax-1.pdf"

Respond with a single word ONLY: "COMPLEX", "STANDARD", or "DIRECT"."""

EXPAND_SYSTEM_PROMPT = """You are a search query expansion assistant. Your goal is to help a search engine find the most relevant chunks in a document store.
Given a user's question, generate exactly 3 diverse phrasal variations or search queries that are semantically equivalent but use different vocabulary or structures (e.g., swapping synonyms like "tax" -> "VAT/GST", "total" -> "amount due/sum").

Respond with a JSON array of strings containing exactly 3 search queries.
Example Output:
[
  "first query variation",
  "second query variation",
  "third query variation"
]

Do not include any preamble, conversational text, or formatting other than the valid JSON array."""

DECOMPOSE_SYSTEM_PROMPT = """You are an expert query decomposition assistant. Your task is to break down a complex, comparative, or multi-step query into a sequence of simpler, self-contained subqueries that can be executed independently.
Each subquery should target a specific file, customer, or fact.
For each subquery, you must also identify if there is a specific document name or ID referenced in the query that this subquery should be filtered to.

Respond with a JSON array of objects. Each object must have two fields:
- "query": The simplified subquery string.
- "document": The specific document name referenced (e.g., "demo-invoice-no-tax-1.pdf"), or null if it applies globally or no specific document can be inferred.

Example Input: "Compare the invoice numbers of demo-invoice-no-tax-1.pdf and invoice_Steve Carroll_22489.pdf"
Example Output:
[
  {"query": "What is the invoice number?", "document": "demo-invoice-no-tax-1.pdf"},
  {"query": "What is the invoice number?", "document": "invoice_Steve Carroll_22489.pdf"}
]

Do not include any preamble, conversational text, explanation, or formatting other than the valid JSON array."""


class QueryRewriter:
    def __init__(
        self,
        groq_client: Optional[Any] = None,
        groq_model: str = "llama-3.3-70b-versatile",
        ollama_client: Optional[Any] = None,
        ollama_model: str = "llama3.2:3b",
    ):
        self.groq_client = groq_client
        self.groq_model = groq_model
        self.ollama_client = ollama_client
        self.ollama_model = ollama_model

    def _call_llm(self, system_instructions: str, user_content: str, llm_provider: str = "ollama") -> str:
        """Helper to invoke the selected LLM provider with a fast, zero-temperature call."""
        if llm_provider == "groq" and self.groq_client:
            client = self.groq_client
            model = self.groq_model
        else:
            client = self.ollama_client
            model = self.ollama_model

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.0,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error during query transformation LLM call ({llm_provider}): {e}")
            raise e

    def route_query(self, query: str, llm_provider: str = "ollama") -> str:
        """Classify a query as COMPLEX, STANDARD, or DIRECT."""
        try:
            result = self._call_llm(ROUTE_SYSTEM_PROMPT, f"Query: {query}", llm_provider=llm_provider)
            # Standardize output
            cleaned = result.strip().upper()
            if "COMPLEX" in cleaned:
                return "COMPLEX"
            elif "STANDARD" in cleaned:
                return "STANDARD"
            else:
                return "DIRECT"
        except Exception as e:
            logger.warning(f"Failed to route query due to LLM error: {e}. Falling back to DIRECT.")
            return "DIRECT"

    def expand_query(self, query: str, llm_provider: str = "ollama") -> List[str]:
        """Generate 3 phrasal variations of the query to expand retrieval recall."""
        fallback = [query]
        try:
            result = self._call_llm(EXPAND_SYSTEM_PROMPT, f"Query: {query}", llm_provider=llm_provider)
            
            # JSON extraction and parsing
            json_str = self._extract_json_array(result)
            if json_str:
                variations = json.loads(json_str)
                if isinstance(variations, list) and len(variations) > 0:
                    # Clean up variations and ensure they are strings
                    cleaned_vars = [str(v).strip() for v in variations if v]
                    if cleaned_vars:
                        # Prepend original query to variations
                        if query not in cleaned_vars:
                            cleaned_vars = [query] + cleaned_vars[:2]
                        return cleaned_vars
            
            # Non-JSON fallback parsing (if LLM returned numbered list)
            lines = [line.strip() for line in result.split("\n") if line.strip()]
            parsed_lines = []
            for line in lines:
                # Remove numbers, quotes, dashes, bullets
                cleaned = re.sub(r'^(\d+[\.\)]|[-*\u2022])\s*', '', line).strip('"\' \t')
                if cleaned and cleaned != query:
                    parsed_lines.append(cleaned)
            
            if parsed_lines:
                return [query] + parsed_lines[:2]
                
            return fallback
        except Exception as e:
            logger.warning(f"Failed to expand query: {e}. Returning original query.")
            return fallback

    def decompose_query(self, query: str, llm_provider: str = "ollama") -> List[Dict[str, Any]]:
        """Decompose a complex comparison query into discrete subqueries targeted at specific files."""
        fallback = [{"query": query, "document": None}]
        try:
            result = self._call_llm(DECOMPOSE_SYSTEM_PROMPT, f"Query: {query}", llm_provider=llm_provider)
            
            # JSON extraction and parsing
            json_str = self._extract_json_array(result)
            if json_str:
                subqueries = json.loads(json_str)
                if isinstance(subqueries, list) and len(subqueries) > 0:
                    cleaned_subs = []
                    for item in subqueries:
                        if isinstance(item, dict) and "query" in item:
                            q = str(item["query"]).strip()
                            doc = item.get("document")
                            doc_str = str(doc).strip() if doc else None
                            if q:
                                cleaned_subs.append({"query": q, "document": doc_str})
                    if cleaned_subs:
                        return cleaned_subs

            # Regular expression fallback if LLM outputs markdown bullets/lists
            # We look for lines containing common file extensions (.pdf)
            lines = [line.strip() for line in result.split("\n") if line.strip()]
            parsed_subs = []
            for line in lines:
                cleaned_line = re.sub(r'^(\d+[\.\)]|[-*\u2022])\s*', '', line).strip('"\' \t')
                if cleaned_line:
                    # Check for doc name in line
                    pdf_match = re.search(r'([\w\-_\.]+\.pdf)', cleaned_line, re.IGNORECASE)
                    doc_name = pdf_match.group(1) if pdf_match else None
                    # Clean up the query
                    parsed_subs.append({
                        "query": cleaned_line,
                        "document": doc_name
                    })
            if parsed_subs:
                return parsed_subs

            return fallback
        except Exception as e:
            logger.warning(f"Failed to decompose query: {e}. Returning fallback.")
            return fallback

    def _extract_json_array(self, text: str) -> Optional[str]:
        """Helper to extract a JSON array from string block (deals with LLM markdown wrapping)."""
        match = re.search(r'(\[[\s\S]*\])', text)
        if match:
            return match.group(1)
        return None
