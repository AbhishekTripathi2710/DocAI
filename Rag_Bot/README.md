# RAG Bot - Retrieval Augmented Generation Pipeline

A comprehensive Retrieval Augmented Generation (RAG) system designed to extract, process, and intelligently retrieve information from PDF documents, combining dense and sparse retrieval methods for optimal search results.

---

## 📁 Project Structure

```
src/
├── embeddings/          # Dense vector embeddings and storage
├── extraction/          # PDF parsing and data extraction
├── preprocessing/       # Text chunking and optimization
└── rag/                 # RAG chain and prompt management
```

---

## 🏗️ Architecture Overview

The RAG pipeline follows a multi-stage architecture:

```
PDF Document
    ↓
[Extraction Layer] → Parse text, tables, and structured data
    ↓
[Preprocessing Layer] → Chunk and optimize content
    ↓
[Embedding Layer] → Generate vector embeddings + BM25 index
    ↓
[Retrieval Layer] → Hybrid retrieval (dense + sparse)
    ↓
[RAG Chain] → Generate answers with LLM
```

---

## 📂 Folder Structure & Components

### 1. **embeddings/** - Vector Embeddings & Storage
Handles dense vector embeddings using SentenceTransformers and ChromaDB for efficient similarity search.

#### Files:
- **`embedder.py`** - Main embedding module
  - `ChunkEmbedder` class: Wrapper around SentenceTransformers + ChromaDB
  - Generates embeddings for text chunks using pre-trained models
  - Stores embeddings in ChromaDB for persistent vector storage
  - Provides similarity search and retrieval capabilities
  - Default model: `all-MiniLM-L6-v2` (lightweight, effective)
  - Features:
    - Add/update chunks with embeddings
    - Query by semantic similarity
    - Optional persistence to disk
    - Metadata filtering support

- **`__init__.py`** - Package initialization

---

### 2. **extraction/** - PDF Parsing & Data Extraction
Core module for extracting text, tables, and structured data from PDF documents.

#### Files:
- **`parser.py`** - Configuration & utilities
  - Lightweight helper functions (no heavy dependencies)
  - Configuration constants:
    - `TEXT_X_TOLERANCE` & `TEXT_Y_TOLERANCE`: PDF text tolerance levels
    - `TABLE_SETTINGS`: pdfplumber table detection strategy (line-based)
  - Common validation and utility functions used across extractors
  - Keeps dependencies minimal for fast imports

- **`text_extractor.py`** - Text content extraction
  - Extracts layout-aware text blocks from PDF pages
  - Preserves text structure and hierarchy
  - `extract_layout_blocks()`: Main function to get text with layout info
  - Handles different text roles (title, heading, body text)
  - Useful for maintaining document semantics

- **`table_extractor.py`** - Table detection & extraction
  - `extract_tables()`: Detects and extracts all tables from a page
  - `is_valid_table()`: Validates extracted table quality
  - `process_table()`: Converts raw table data to structured format
  - Handles multiple table layouts:
    - `extract_flow_layout_table()`: For dynamically positioned tables
    - `try_parse_flow_layout_table()`: Flow-based table detection
    - `try_parse_semi_structured_table()`: Semi-structured data
  - Returns tables as list of dicts with columns and rows

- **`pipeline.py`** - Orchestration layer
  - `is_bank_statement()`: Document type detection
  - Combines text and table extractors
  - Main extraction workflow:
    1. Load PDF with pdfplumber
    2. Extract text blocks and tables per page
    3. Classify document type
    4. Merge and structure results
  - Returns comprehensive extraction result with all document content

- **`bm25_index.py`** - Sparse keyword-based retrieval
  - `BM25Index` class: Efficient keyword search using BM25 algorithm
  - `build()`: Create index from chunks
  - `search()`: Find top-k chunks by keyword relevance
  - Complements dense retrieval for better recall
  - Independent of embeddings (can work with text alone)

- **`hybrid_retriever.py`** - Combined dense + sparse retrieval
  - `HybridRetriever` class: Combines ChromaDB (dense) + BM25 (sparse)
  - `retrieve()`: Main method that:
    1. Performs dense retrieval (semantic similarity)
    2. Performs sparse retrieval (keyword matching)
    3. Fuses results using Reciprocal Rank Fusion (RRF)
    4. Returns ranked top-k chunks
  - Parameters:
    - `dense_weight`: Balance between dense (0.5) and sparse retrieval
    - `where`: Optional metadata filters
    - `k_rrf`: RRF parameter (tunable, default 60)

- **`__init__.py`** - Package initialization

---

### 3. **preprocessing/** - Text Chunking & Optimization
Transforms extracted PDF data into optimized searchable chunks for embedding and retrieval.

#### Files:
- **`chunker.py`** - Main chunking module
  - Converts extracted JSON to searchable chunks
  - Key classes & functions:
    - `_row_to_sentence()`: Converts table rows to natural language
    - `_row_to_json_string()`: Keeps rows as JSON for exact matching
    - `_optimise_kv_text()`: Improves embedding quality for key-value pairs
    - `_merge_small_plain_chunks()`: Combines small text blocks (< 300 chars)
  - Table chunking strategies:
    - `"sentence"`: Convert rows to readable sentences
    - `"raw_json"`: Keep as structured JSON (for exact matching)
    - `"auto"`: Choose strategy based on table complexity
  - Features:
    - Smart merging of small chunks for better context
    - Metadata preservation (page number, source, type)
    - Type classification (text_block, table_row, key_value)
    - Optimal chunk size for embedding models

- **`__init__.py`** - Package initialization

---

### 4. **rag/** - RAG Chain & Prompt Management
Implements the Retrieval-Augmented Generation loop with LLM integration.

#### Files:
- **`chain.py`** - RAG orchestration
  - `RAGChain` class: Main RAG system
  - Methods:
    - `answer()`: Dense-only retrieval + generation
    - `answer_hybrid()`: Hybrid retrieval + generation
    - `_generate()`: LLM response generation (internal)
  - Features:
    - Flexible retrieval mode selection
    - Optional metadata filtering
    - Configurable top-k retrieval
    - Support for multiple LLM models
  - Integration:
    - Uses `HybridRetriever` for retrieval
    - Uses OpenAI client for LLM calls
    - Respects `MAX_CONTEXT_CHARS` limit (~2000 tokens)
    - Default model: `gpt-4o-mini`

- **`prompt.py`** - Prompt engineering & formatting
  - `SYSTEM_INSTRUCTIONS`: Defines LLM behavior
    - Emphasizes precision and context-based answers
    - Prevents hallucination
    - Prefers structured data (tables, key-value pairs)
  - `build_prompt()`: Constructs LLM prompt with context
  - `format_context()`: Formats retrieved chunks for presentation
  - Features:
    - Raw JSON integration for exact values
    - Metadata annotation (page numbers, types)
    - Structured vs. unstructured data formatting

- **`__init__.py`** - Package initialization

---

## 🔄 Data Flow Example

```
1. PDF Upload
   ↓
2. Extract Text & Tables (extraction/pipeline.py)
   ├── Text blocks with layout info
   ├── Table data as structured JSON
   └── Document type classification
   ↓
3. Preprocessing (preprocessing/chunker.py)
   ├── Merge small text blocks
   ├── Convert table rows to sentences/JSON
   └── Attach metadata (page, type, source)
   ↓
4. Embedding (embeddings/embedder.py)
   ├── Generate vector embeddings (SentenceTransformers)
   └── Store in ChromaDB
   ↓
5. Indexing (extraction/bm25_index.py)
   └── Build BM25 index for keyword search
   ↓
6. Retrieval (extraction/hybrid_retriever.py)
   ├── Dense search in ChromaDB
   ├── Sparse search with BM25
   ├── Fuse results with RRF
   └── Return top-k relevant chunks
   ↓
7. Generation (rag/chain.py)
   ├── Format retrieved context (rag/prompt.py)
   ├── Call LLM with prompt
   └── Return answer to user
```

---

## 🔧 Key Features

### 1. **Hybrid Retrieval**
   - Combines semantic (dense) and keyword (sparse) search
   - Uses Reciprocal Rank Fusion (RRF) for optimal ranking
   - Better recall and precision than single method

### 2. **Multi-Modal Extraction**
   - Handles text content and tables
   - Automatic document type detection
   - Preserves document structure and formatting

### 3. **Intelligent Chunking**
   - Automatic chunk size optimization
   - Metadata preservation for traceability
   - Smart merging of small text blocks
   - Multiple table formatting strategies

### 4. **LLM Integration**
   - OpenAI API support (and Ollama optional)
   - Configurable model selection
   - Context window management
   - Hallucination prevention via precise prompting

### 5. **Persistent Storage**
   - ChromaDB with disk persistence
   - BM25 index caching
   - Metadata filtering for targeted retrieval

---

## 💡 Usage Patterns

### Basic Setup
```python
from embeddings.embedder import ChunkEmbedder
from extraction.bm25_index import BM25Index
from extraction.hybrid_retriever import HybridRetriever
from rag.chain import RAGChain

# Initialize embedder
embedder = ChunkEmbedder(persist_directory="./db")

# Build BM25 index
bm25 = BM25Index()
bm25.build(chunks)

# Create RAG chain
rag = RAGChain(embedder, bm25_index=bm25)

# Answer questions
answer = rag.answer_hybrid("What is the balance?")
```

### Extract & Process PDF
```python
from extraction.pipeline import extract_from_pdf
from preprocessing.chunker import chunk_document

# Extract
document = extract_from_pdf("file.pdf")

# Preprocess
chunks = chunk_document(document)

# Embed
embedder.add_chunks(chunks)
```

---

## 📊 Configuration & Tuning

| Component | Key Parameters | Default |
|-----------|---|---|
| **Embedder** | `model_name` | `all-MiniLM-L6-v2` |
| **Chunker** | Table strategy | `"auto"` |
| **Chunker** | Merge threshold | `300` chars |
| **BM25** | Tokenization | Word-level split |
| **Hybrid Retriever** | RRF parameter | `k_rrf=60` |
| **Hybrid Retriever** | Dense weight | `0.5` |
| **RAG Chain** | LLM model | `gpt-4o-mini` |
| **RAG Chain** | Max context | `8000` chars |

---

## 🚀 Performance Considerations

- **Embeddings**: Lightweight model for fast inference
- **BM25**: O(log n) lookup with pre-built index
- **ChromaDB**: In-memory with optional persistence
- **Chunking**: Automatic size optimization to fit embedding models
- **Hybrid Retrieval**: Balanced accuracy and speed

---

## 📝 Output Formats

### Extracted Document
```json
{
  "pages": [
    {
      "text_blocks": [...],
      "tables": [...],
      "page_num": 1,
      "type": "bank_statement"
    }
  ]
}
```

### Chunks (for embedding)
```json
{
  "text": "Account Balance: $5,000",
  "type": "key_value",
  "metadata": {
    "page": 1,
    "source": "bank_statement",
    "raw_json": "{\"key\": \"Account Balance\", \"value\": \"$5,000\"}"
  }
}
```

### Retrieval Results
```python
[
  {
    "text": "...",
    "metadata": {...},
    "type": "text_block",
    "score": 0.95  # similarity score
  },
  ...
]
```

---

## 🔗 Dependencies

### Core Libraries
- **pdfplumber**: PDF parsing and text extraction
- **chromadb**: Vector database
- **sentence-transformers**: Embedding model
- **rank-bm25**: BM25 implementation
- **openai**: LLM API client

### Installation
```bash
pip install pdfplumber chromadb sentence-transformers rank-bm25 openai
```

---

## 📄 License & Notes

- Modular architecture allows easy component swapping
- Type hints included for IDE support
- Minimal dependencies in core modules
- Configuration-driven behavior for flexibility

---

## 🎯 Next Steps

- Implement document upload interface
- Add more LLM model support
- Extend extraction for additional document types
- Add result caching layer
- Implement feedback loop for relevance improvement
