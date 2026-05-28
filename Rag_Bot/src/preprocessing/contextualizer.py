import logging
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class LocalContextualizer:
    def __init__(
        self, 
        base_url: str = "http://localhost:11434", 
        model: str = "llama3.2:3b",
        max_parallel: int = 2 # Reduced for local stability
    ):
        # Strip /v1 if present for native Ollama API calls
        api_base = base_url.rstrip("/")
        if api_base.endswith("/v1"):
            api_base = api_base[:-3]
            
        self.base_url = f"{api_base}/api/generate"
        self.model = model
        self.max_parallel = max_parallel
        self.client = httpx.AsyncClient(timeout=120.0) # Increased timeout for local LLM

    def _get_type_specific_instructions(self, doc_type: str, doc_name: str) -> dict:
        """
        Returns type-specific instructions and examples for the LLM prompt.
        Supports: invoice, bank statement, research paper, legal document
        """
        type_lower = doc_type.lower().replace(" ", "_")
        
        if type_lower in ("bank_statement", "bank statement"):
            return {
                "role": "You are a precise financial document analyst.",
                "description": "a financial transaction",
                "content_types": "'transaction', 'entry', 'line item', 'record', 'summary', 'balance'",
                "entity_hint": "Use the document context to identify the Account Holder or Customer. Do NOT fabricate names.",
                "extra": ""
            }
        elif type_lower in ("invoice",):
            return {
                "role": "You are a precise invoice analyst.",
                "description": "an invoice line item",
                "content_types": "'line item', 'entry', 'total', 'subtotal', 'invoice detail', 'record'",
                "entity_hint": "Use the document context to identify the Vendor, Customer, or Bill To entity. Do NOT fabricate names.",
                "extra": ""
            }
        elif type_lower in ("research_paper", "research paper", "paper", "academic"):
            return {
                "role": "You are a precise research paper analyst.",
                "description": "a research paper section",
                "content_types": "'section', 'paragraph', 'abstract', 'citation', 'reference', 'figure caption', 'equation', 'table'",
                "entity_hint": "This is an academic document. Describe the scholarly content. Do NOT invent financial transactions or customer names.",
                "extra": "Focus on the academic topic, methodology, results, or references discussed in the chunk."
            }
        elif type_lower in ("legal_document", "legal document", "legal"):
            return {
                "role": "You are a precise legal document analyst.",
                "description": "a legal document clause",
                "content_types": "'clause', 'section', 'provision', 'definition', 'exhibit', 'schedule', 'paragraph'",
                "entity_hint": "Use the document context to identify Parties involved only if explicitly mentioned. Do NOT fabricate party names.",
                "extra": "Describe the legal content neutrally — terms, conditions, obligations, or definitions."
            }
        else:
            # Generic fallback for unknown types
            return {
                "role": "You are a precise document analyst.",
                "description": "a document section",
                "content_types": "'section', 'paragraph', 'entry', 'record', 'item', 'field'",
                "entity_hint": "Describe the content based on what is actually in the chunk. Do NOT fabricate details.",
                "extra": ""
            }

    async def contextualize_chunks(
        self, 
        chunks: List[Dict[str, Any]], 
        doc_name: str, 
        doc_type: str = "document"
    ) -> List[Dict[str, Any]]:
        """
        Parallelizes the contextualization of multiple chunks with document identity.
        Uses the document name and type as the identity anchor instead of scanning
        raw chunk text (which could contain cross-document data contamination).
        """
        logger.info(f"Contextualizing {len(chunks)} chunks using {self.model}...")
        
        # Use document name and type as the identity anchor
        global_truth = f"Document: {doc_name}, Type: {doc_type}"
        
        semaphore = asyncio.Semaphore(self.max_parallel)
        
        async def process_with_limit(idx):
            async with semaphore:
                return await self._process_single_chunk(chunks, idx, doc_name, doc_type, global_truth)

        tasks = [process_with_limit(i) for i in range(len(chunks))]
        results = await asyncio.gather(*tasks)
        
        # Update chunks with their new situational text
        for i, context_text in enumerate(results):
            if context_text:
                chunks[i]["original_text"] = chunks[i]["text"]
                chunks[i]["text"] = f"{context_text}\n\n{chunks[i]['text']}"
                chunks[i]["metadata"]["contextualized"] = True
            else:
                # Fallback to a basic heuristic prefix if AI fails
                fallback = f"[Manual Context] This chunk contains {chunks[i].get('type', 'document')} data from {doc_name}."
                chunks[i]["original_text"] = chunks[i]["text"]
                chunks[i]["text"] = f"{fallback}\n\n{chunks[i]['text']}"
                chunks[i]["metadata"]["contextualized"] = False
                
        return chunks

    async def _process_single_chunk(
        self, 
        chunks: List[Dict[str, Any]], 
        current_idx: int, 
        doc_name: str, 
        doc_type: str,
        global_truth: str
    ) -> Optional[str]:
        """
        Generates context for a single chunk.
        """
        window_size = 1
        start = max(0, current_idx - window_size)
        end = min(len(chunks), current_idx + window_size + 1)
        
        surrounding_context = "\n---\n".join([chunks[i]["text"] for i in range(start, end) if i != current_idx])
        chunk_text = chunks[current_idx]["text"]

        # Get type-specific instructions
        type_info = self._get_type_specific_instructions(doc_type, doc_name)

        prompt = f"""<Role>{type_info['role']}</Role>

<Global_Truth_Header>
{global_truth}
</Global_Truth_Header>

<Local_Nearby_Context>
{surrounding_context}
</Local_Nearby_Context>

<Chunk_To_Describe>
{chunk_text}
</Chunk_To_Describe>

<Instruction>
Create a concise, one‑sentence description of the Chunk for high‑precision retrieval.
Follow these rules strictly:

1. CONTENT DESCRIPTION:
   Describe what the chunk actually contains. Use appropriate content types such as: {type_info['content_types']}.
   {type_info['extra']}

2. ENTITY RESOLUTION:
   {type_info['entity_hint']}

3. STRUCTURE:
   Start with "This chunk contains". Describe the content naturally based on what is actually present in the chunk text.
   Mention the document name ({doc_name}) and type ({doc_type}) if relevant.

4. DO NOT invent dates, monetary amounts, names, or entities that are not clearly present in the chunk text.
   If no date or amount is present, simply describe the topic or content type.

5. Return ONLY the final sentence starting with "This chunk". No preamble, no extra commentary.
</Instruction>

Return ONLY the sentence starting with "This chunk". NO PREAMBLE.
"""
        
        for attempt in range(3):
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0}
                }
                
                response = await self.client.post(self.base_url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                context_sentence = result.get("response", "").strip()
                
                # Clean up potential LLM chatter
                if "\n" in context_sentence:
                    context_sentence = context_sentence.split("\n")[0]
                
                return context_sentence
            except Exception as e:
                if attempt < 2:
                    logger.warning(f"Retry {attempt + 1} for chunk {current_idx} after error: {e}")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"Failed to contextualize chunk {current_idx} after 3 attempts: {e}")
                    return None

    async def close(self):
        await self.client.aclose()