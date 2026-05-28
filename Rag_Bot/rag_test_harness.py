#!/usr/bin/env python3
"""
Advanced RAG Evaluation Suite (Using Project Pipeline)
------------------------------------------------------
Automated testing and comparison of LLaMA 3 (Local) vs LLaMA 3.3 70B (Groq).
Evaluates Accuracy, Faithfulness, Hallucination, and Latency using the ACTUAL 
project extraction and chunking pipeline.

Usage:
    python rag_test_harness.py
"""

import os
import sys
import time
import json
import uuid
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add src to path for imports
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.getcwd(), "src", ".env"))
    
    # Project Pipeline Imports
    from extraction.pipeline import extract_pdf
    from preprocessing.chunker import chunk_extracted_data
    from embeddings.embedder import ChunkEmbedder
    from rag.chain import RAGChain
    # We will use a custom prompt builder to enforce the evaluation strictness
    from rag.prompt import format_context
    
    from openai import OpenAI
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Ensure you are running this from the project root and requirements are installed.")
    sys.exit(1)

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
DOC_DIR = "./test/files"
OUTPUT_DIR = "./test/evaluation"
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# Use config values or defaults
MODEL_LOCAL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
MODEL_GROQ = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Strict Evaluation Prompt
STRICT_SYSTEM_PROMPT = (
    "Answer ONLY from the provided context. "
    "If the answer is not present, respond with: NOT FOUND. "
    "Do NOT guess or hallucinate."
)

def build_eval_prompt(question: str, chunks: List[Dict[str, Any]]) -> str:
    """Builds a prompt using the project's formatting but the evaluation's strictness."""
    context = format_context(chunks)
    return f"{STRICT_SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"

# -------------------------------------------------------------------
# Dataset Mapping (Document 1 to 19)
# -------------------------------------------------------------------
EVAL_DATASET = [
    {"id": "Doc_1", "file": "261235518399061.pdf", "questions": ["What is the total amount including tax?", "Who is the invoice issued to and what is their address?"]},
    {"id": "Doc_2", "file": "Cream and Pink Modern Professional Invoice.pdf", "questions": ["What is the final total amount after tax?", "Which service has the highest cost?"]},
    {"id": "Doc_3", "file": "Black And Gray Minimal Freelancer Invoice.pdf", "questions": ["What is the total invoice amount?", "What items and quantities are listed?"]},
    {"id": "Doc_4", "file": "Black and White Minimalist Professional Invoice.pdf", "questions": ["What is the total payable amount after tax?", "What are the hourly rates and hours?"]},
    {"id": "Doc_5", "file": "672652313-Statement-748xxxx8590-09092023-201306.pdf", "questions": ["What is the closing balance?", "What is the largest credit transaction and its date?"]},
    {"id": "Doc_6", "file": "Invoice_2531382157.pdf", "questions": ["What is the total amount due in INR?", "Which AWS service has the highest cost?"]},
    {"id": "Doc_7", "file": "Black and White Simple Minimalist Invoice A4.pdf", "questions": ["What is the total balance due?", "Which product has the highest cost?"]},
    {"id": "Doc_8", "file": "demo-invoice-no-tax-2.pdf", "questions": ["What is the total invoice amount?", "Which item has the highest line total?"]},
    {"id": "Doc_9", "file": "demo-invoice-no-tax-4.pdf", "questions": ["What is the total invoice value?", "Which product has the highest quantity?"]},
    {"id": "Doc_10", "file": "demo-invoice-no-tax-8.pdf", "questions": ["What is the final total including shipping?", "What is the cost and quantity of Material A?"]},
    {"id": "Doc_11", "file": "demo-invoice-no-tax-9.pdf", "questions": ["What is the total invoice amount?", "Which item contributes the most to total?"]},
    {"id": "Doc_12", "file": "demo-invoice-no-tax-3.pdf", "questions": ["What is the total amount due?", "Who is the invoice billed to?"]},
    {"id": "Doc_13", "file": "demo-invoice-no-tax-1.pdf", "questions": ["What is the total amount including shipping?", "What is the difference between subtotal and total?"]},
    {"id": "Doc_14", "file": "demo-invoice-no-tax-4.pdf", "questions": ["What is the total invoice amount?", "Which product has the highest quantity?"]},
    {"id": "Doc_15", "file": "demo-invoice-no-tax-10.pdf", "questions": ["What is the invoice balance due?", "What are the invoice and due dates?"]},
    {"id": "Doc_16", "file": "demo-invoice-swiss-qr.pdf", "questions": ["What is the total amount including VAT?", "What is the VAT rate and VAT amount?"]},
    {"id": "Doc_17", "file": "Grey and White Minimal Business Invoice.pdf", "questions": ["What is the final total amount?", "What services and prices are listed?"]},
    {"id": "Doc_18", "file": "ilide.info-canara-bank-statement-pr_4df916cafa520757ac56f0db1750b751.pdf", "questions": ["What is the final account balance?", "What is the total of all ATM withdrawals?"]},
    {"id": "Doc_19", "file": "purchase-order-1.pdf", "questions": ["What is the purchase order number?", "What is the total cost of all items?"]}
]

# -------------------------------------------------------------------
# Evaluation Metrics Logic (LLM as Judge)
# -------------------------------------------------------------------
class Evaluator:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
        self.judge_model = "llama-3.3-70b-versatile"

    def evaluate_response(self, question: str, context: str, answer: str) -> Dict[str, Any]:
        if answer == "NOT FOUND":
            return {"accuracy": 0, "faithfulness": 1, "hallucination": 0, "explanation": "Correctly identified missing info"}

        prompt = (
            f"You are an objective RAG evaluator.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {question}\n\n"
            f"ANSWER: {answer}\n\n"
            f"Evaluate the answer based on the following (Respond in JSON only):\n"
            f"1. accuracy: Score 1 if correct relative to context, 0 otherwise.\n"
            f"2. faithfulness: Score 1 if the answer is grounded ONLY in the context, 0 otherwise.\n"
            f"3. hallucination: Score 1 if the answer contains info NOT in the context, 0 otherwise.\n"
            f"4. explanation: Short reason for scores.\n"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.judge_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"accuracy": 0, "faithfulness": 0, "hallucination": 0, "explanation": f"Eval Failed: {e}"}

# -------------------------------------------------------------------
# Main Evaluation Loop
# -------------------------------------------------------------------
def run_evaluation():
    print("Starting Automated RAG Evaluation using ACTUAL project pipeline...")
    
    if not os.getenv("GROQ_API_KEY"):
        print("FATAL: GROQ_API_KEY missing.")
        sys.exit(1)

    # Initialize Embedder (temp collection)
    # Using persist_directory to avoid memory issues, but we'll clean up
    embedder = ChunkEmbedder(collection_name="eval_temp", persist_directory="./chroma_db_eval")
    
    # Initialize RAG Chain
    rag = RAGChain(
        embedder=embedder,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        groq_model=MODEL_GROQ,
        ollama_model=MODEL_LOCAL
    )
    
    evaluator = Evaluator()
    raw_results = []

    for doc in EVAL_DATASET:
        doc_id = doc["id"]
        filename = doc["file"]
        pdf_path = os.path.join(DOC_DIR, filename)
        
        if not os.path.exists(pdf_path):
            print(f"Skipping {filename} (not found)")
            continue
            
        print(f"\nProcessing {doc_id} ({filename}) using layout-aware pipeline...")
        
        # 1. ACTUAL Extraction Pipeline
        try:
            extracted_data = extract_pdf(pdf_path)
            chunks = chunk_extracted_data(extracted_data)
            
            # Tag chunks with doc_id for cleanup
            for c in chunks:
                c["metadata"]["doc_id"] = doc_id
                
            embedder.add_chunks(chunks)
            print(f"  Extracted {len(chunks)} chunks.")
        except Exception as e:
            print(f"  Extraction failed for {filename}: {e}")
            continue

        # 2. Query Questions
        for q in doc["questions"]:
            print(f"  Querying: {q}")
            
            # Use the strict prompt builder
            results = embedder.query(q, top_k=5)
            retrieved_chunks = []
            for d, m in zip(results["documents"][0], results["metadatas"][0]):
                retrieved_chunks.append({"text": d, "metadata": m})
            
            context = format_context(retrieved_chunks)
            
            for provider in ["ollama", "groq"]:
                provider_name = "Ollama (Local)" if provider == "ollama" else "Groq (70B)"
                start_time = time.time()
                
                # We call the model directly with the strict prompt
                # instead of using rag.answer() which uses the default prompt
                eval_prompt = build_eval_prompt(q, retrieved_chunks)
                
                # We reuse the RAGChain's client management but with our custom prompt
                if provider == "groq":
                    client, model = rag.groq_client, rag.groq_model
                else:
                    client, model = rag.ollama_client, rag.ollama_model
                
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": eval_prompt}],
                        temperature=0.0,
                        max_tokens=1024,
                        timeout=60 # Add timeout to avoid hangs
                    )
                    answer = response.choices[0].message.content.strip()
                except Exception as e:
                    answer = f"ERROR: {e}"
                
                latency = time.time() - start_time
                eval_metrics = evaluator.evaluate_response(q, context, answer)
                
                res = {
                    "Document": doc_id,
                    "Question": q,
                    "Model": provider_name,
                    "Answer": answer,
                    "Accuracy": eval_metrics.get("accuracy", 0),
                    "Faithfulness": eval_metrics.get("faithfulness", 0),
                    "Hallucination": eval_metrics.get("hallucination", 0),
                    "Latency": round(latency, 2),
                    "Reason": eval_metrics.get("explanation", "")
                }
                raw_results.append(res)
                print(f"    [{provider_name}] Acc: {res['Accuracy']}, Lat: {res['Latency']}s")

        # 3. Cleanup Chunks for this Document
        embedder.collection.delete(where={"doc_id": doc_id})
        print(f"  Cleaned up data for {doc_id}")

    # Generate Report
    generate_report(raw_results)

def generate_report(results):
    if not results:
        print("No results to report.")
        return

    # CSV
    raw_csv = os.path.join(OUTPUT_DIR, "raw_results_pipeline.csv")
    with open(raw_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # Aggregation
    agg = {}
    for r in results:
        m = r["Model"]
        if m not in agg: agg[m] = {"acc": [], "hallu": [], "lat": [], "count": 0}
        agg[m]["acc"].append(r["Accuracy"])
        agg[m]["hallu"].append(r["Hallucination"])
        agg[m]["lat"].append(r["Latency"])
        agg[m]["count"] += 1

    report_md = [
        "# RAG Evaluation Report (Full Pipeline)",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "## 1. Aggregated Metrics",
        "| Model | Accuracy | Hallucination Rate | Avg Latency |",
        "| :--- | :--- | :--- | :--- |"
    ]
    
    comp = {}
    for m, data in agg.items():
        avg_acc = sum(data["acc"]) / data["count"]
        avg_hallu = sum(data["hallu"]) / data["count"]
        avg_lat = sum(data["lat"]) / data["count"]
        report_md.append(f"| {m} | {avg_acc:.2%} | {avg_hallu:.2%} | {avg_lat:.2f}s |")
        comp[m] = {"acc": avg_acc, "hallu": avg_hallu, "lat": avg_lat}

    # Error Analysis
    report_md.append("\n## 2. Error Analysis")
    report_md.append("| Doc | Model | Error | Reason |")
    report_md.append("| :--- | :--- | :--- | :--- |")
    for r in results:
        if r["Accuracy"] == 0 or r["Hallucination"] == 1:
            err = "Hallucination" if r["Hallucination"] == 1 else "Incorrect"
            report_md.append(f"| {r['Document']} | {r['Model']} | {err} | {r['Reason']} |")

    # Conclusion
    m1, m2 = list(comp.keys())[0], list(comp.keys())[1]
    best = m1 if comp[m1]["acc"] > comp[m2]["acc"] else m2
    report_md.extend([
        "\n## 3. Conclusion",
        f"**Best Model**: {best}",
        f"This evaluation used the project's layout-aware extraction and chunking pipeline."
    ])

    with open(os.path.join(OUTPUT_DIR, "evaluation_report_pipeline.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_md))

    print(f"\nEvaluation Complete! Report: {OUTPUT_DIR}/evaluation_report_pipeline.md")

if __name__ == "__main__":
    run_evaluation()