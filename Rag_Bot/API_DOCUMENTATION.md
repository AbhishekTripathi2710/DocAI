# RAG Bot API Documentation

Complete REST API documentation for the RAG Bot backend.

## 🚀 Quick Start

### Installation

```bash
# Install FastAPI dependencies
pip install -r requirements-api.txt

# Or install all dependencies
pip install -r requirements.txt
pip install -r requirements-api.txt
```

### Running the Server

```bash
# Development (with auto-reload)
cd src
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Production
cd src
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Access the API

- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

---

## 📋 Environment Variables

Configure the API using environment variables:

```bash
# LLM Configuration (Required)
export OPENAI_API_KEY="sk-..."

# Optional: Override default models
export EMBEDDING_MODEL="all-MiniLM-L6-v2"
export LLM_MODEL="gpt-4o-mini"

# Optional: Database paths
export CHROMA_DB_PATH="./chroma_db"
export BM25_INDEX_PATH="./bm25_index"
export UPLOAD_DIR="./uploads"
export METADATA_STORE_PATH="./metadata.json"

# Optional: Logging
export LOG_LEVEL="INFO"
export LOG_FILE="./logs/api.log"
```

---

## 🔌 API Endpoints

### Health & Status

#### `GET /ping`
Simple health check endpoint.

**Response:**
```json
{
  "message": "pong",
  "timestamp": "2024-01-15T10:30:45.123456"
}
```

#### `GET /health`
Get detailed system health status.

**Response:**
```json
{
  "status": "healthy",
  "embedder_ready": true,
  "bm25_index_ready": true,
  "documents_count": 5,
  "total_chunks": 1250
}
```

---

### Document Management

#### `POST /documents/upload`
Upload and process a PDF document.

**Request:**
- `file` (form-data): PDF file (max 50MB)

**Response:**
```json
{
  "doc_id": "doc_a1b2c3d4e5f6",
  "file_name": "document.pdf",
  "pages": 15,
  "chunks_count": 145,
  "created_at": "2024-01-15T10:30:45.123456",
  "document_type": "bank_statement"
}
```

**Example (cURL):**
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "accept: application/json" \
  -F "file=@document.pdf"
```

**Example (Python):**
```python
import requests

with open("document.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(
        "http://localhost:8000/documents/upload",
        files=files
    )
    print(response.json())
```

---

#### `GET /documents/`
List all uploaded documents.

**Response:**
```json
{
  "documents": [
    {
      "doc_id": "doc_a1b2c3d4e5f6",
      "file_name": "document1.pdf",
      "pages": 15,
      "chunks_count": 145,
      "created_at": "2024-01-15T10:30:45.123456",
      "document_type": "bank_statement"
    },
    {
      "doc_id": "doc_x9y8z7w6v5u4",
      "file_name": "document2.pdf",
      "pages": 10,
      "chunks_count": 95,
      "created_at": "2024-01-15T11:15:30.654321",
      "document_type": "invoice"
    }
  ],
  "total": 2
}
```

---

#### `GET /documents/{doc_id}`
Get information about a specific document.

**Parameters:**
- `doc_id` (path): Document ID

**Response:**
```json
{
  "doc_id": "doc_a1b2c3d4e5f6",
  "file_name": "document.pdf",
  "pages": 15,
  "chunks_count": 145,
  "created_at": "2024-01-15T10:30:45.123456",
  "document_type": "bank_statement"
}
```

---

#### `DELETE /documents/{doc_id}`
Delete a document and remove it from all indexes.

**Parameters:**
- `doc_id` (path): Document ID

**Response:**
```json
{
  "message": "Document deleted successfully",
  "doc_id": "doc_a1b2c3d4e5f6",
  "chunks_deleted": 145
}
```

---

### Query & Retrieval

#### `POST /query/dense`
Query using dense retrieval only (semantic similarity).

**Request:**
```json
{
  "query": "What is the account balance?",
  "doc_id": "doc_a1b2c3d4e5f6",
  "top_k": 5,
  "include_metadata": true
}
```

**Parameters:**
- `query` (required): Question or search query
- `doc_id` (optional): Specific document ID. If None, searches all documents
- `top_k` (optional): Number of top results (1-20, default 5)
- `include_metadata` (optional): Include metadata in results (default true)

**Response:**
```json
{
  "query": "What is the account balance?",
  "answer": "The account balance is $5,000.00 as of January 15, 2024.",
  "retrieved_chunks": [
    {
      "text": "Account Balance: $5,000.00",
      "metadata": {
        "page": 1,
        "source": "bank_statement",
        "doc_id": "doc_a1b2c3d4e5f6"
      },
      "type": "key_value",
      "score": 0.9523
    }
  ],
  "retrieval_mode": "dense",
  "processing_time_ms": 245.32
}
```

**Example (Python):**
```python
import requests

query_data = {
    "query": "What is the account balance?",
    "top_k": 5
}

response = requests.post(
    "http://localhost:8000/query/dense",
    json=query_data
)

result = response.json()
print(f"Answer: {result['answer']}")
for chunk in result['retrieved_chunks']:
    print(f"- {chunk['text']} (score: {chunk['score']})")
```

---

#### `POST /query/hybrid`
Query using hybrid retrieval (dense + sparse with RRF).

**Request:**
```json
{
  "query": "What is the account balance?",
  "doc_id": null,
  "top_k": 5,
  "mode": "hybrid",
  "include_metadata": true
}
```

**Parameters:** Same as dense retrieval

**Response:** Same format as dense retrieval, but with `"retrieval_mode": "hybrid"`

**Note:** Hybrid retrieval combines:
- **Dense retrieval**: Semantic similarity using embeddings
- **Sparse retrieval**: Keyword matching using BM25
- **Ranking**: Reciprocal Rank Fusion (RRF) to combine results

This typically provides better recall and precision than dense-only search.

---

#### `POST /query/ask`
Ask a question with automatic retrieval mode selection.

**Request:**
```json
{
  "query": "What is the account balance?",
  "mode": "hybrid",
  "top_k": 5,
  "doc_id": null
}
```

**Parameters:**
- `query` (required): Question to ask
- `mode` (optional): Retrieval mode - "dense" or "hybrid" (default "hybrid")
- `top_k` (optional): Number of results (1-20, default 5)
- `doc_id` (optional): Specific document to search

**Response:** Same as retrieval responses

This endpoint routes to the appropriate retrieval method based on the `mode` parameter.

---

#### `GET /query/search`
Simple search endpoint using query parameters.

**Parameters (Query String):**
- `q` (required): Search query
- `doc_id` (optional): Document ID
- `top_k` (optional): Number of results (default 5)
- `mode` (optional): Retrieval mode (dense or hybrid, default hybrid)

**Example:**
```bash
curl "http://localhost:8000/query/search?q=What%20is%20the%20balance&top_k=3&mode=hybrid"
```

**Response:** Same as retrieval responses

Convenient for simple searches without complex request bodies.

---

## 📊 Request/Response Models

### QueryRequest
```python
{
    "query": str,                    # Search query (required)
    "doc_id": Optional[str],         # Document ID (optional)
    "top_k": int = 5,               # Number of results (1-20)
    "mode": "dense" | "hybrid",     # Retrieval mode
    "include_metadata": bool = True # Include metadata
}
```

### QueryResponse
```python
{
    "query": str,                    # Original query
    "answer": str,                   # Generated answer
    "retrieved_chunks": [
        {
            "text": str,            # Chunk text
            "metadata": dict,       # Metadata
            "type": str,            # Chunk type
            "score": float          # Relevance score (optional)
        }
    ],
    "retrieval_mode": str,          # Mode used (dense/hybrid)
    "processing_time_ms": float     # Processing time
}
```

### DocumentInfo
```python
{
    "doc_id": str,                   # Document ID
    "file_name": str,                # Original filename
    "pages": int,                    # Number of pages
    "chunks_count": int,             # Number of chunks
    "created_at": str,               # ISO format timestamp
    "document_type": Optional[str]   # Detected document type
}
```

---

## 🔍 Examples

### Complete Workflow

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Check health
health = requests.get(f"{BASE_URL}/health").json()
print(f"System status: {health['status']}")

# 2. Upload a document
with open("bank_statement.pdf", "rb") as f:
    files = {"file": f}
    upload_response = requests.post(
        f"{BASE_URL}/documents/upload",
        files=files
    )
    doc = upload_response.json()
    doc_id = doc["doc_id"]
    print(f"Uploaded: {doc['file_name']} ({doc['pages']} pages)")

# 3. List documents
docs_response = requests.get(f"{BASE_URL}/documents/").json()
print(f"Total documents: {docs_response['total']}")

# 4. Query specific document
query_response = requests.post(
    f"{BASE_URL}/query/hybrid",
    json={
        "query": "What is the current balance?",
        "doc_id": doc_id,
        "top_k": 3
    }
).json()

print(f"\nQuery: {query_response['query']}")
print(f"Answer: {query_response['answer']}")
print(f"Retrieved {len(query_response['retrieved_chunks'])} chunks")
for i, chunk in enumerate(query_response['retrieved_chunks'], 1):
    print(f"  {i}. {chunk['text'][:100]}... (score: {chunk.get('score', 'N/A')})")

# 5. Delete document
delete_response = requests.delete(
    f"{BASE_URL}/documents/{doc_id}"
).json()
print(f"\nDeleted: {delete_response['chunks_deleted']} chunks removed")
```

---

## 🔐 Error Handling

All endpoints return standardized error responses:

**Error Response Format:**
```json
{
  "error": "Error Type",
  "detail": "Detailed error message",
  "status_code": 400
}
```

**Common Status Codes:**
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (document doesn't exist)
- `422`: Validation Error (invalid request format)
- `500`: Internal Server Error

---

## 📈 Performance Tips

1. **Batch Queries**: Process multiple queries sequentially rather than parallel for better resource management

2. **Document Size**: Keep documents under 50MB. Larger documents take longer to process.

3. **Top K Parameter**: Use smaller top_k values (3-5) for faster responses. Larger values (10+) retrieve more context but are slower.

4. **Retrieval Mode**: 
   - Use **dense** for fast semantic search
   - Use **hybrid** for better accuracy (slightly slower)

5. **Metadata Filtering**: Use `doc_id` parameter to search specific documents instead of all documents

6. **Caching**: Implement client-side caching for frequently asked questions

---

## 🐛 Troubleshooting

### API won't start
- **Check**: OPENAI_API_KEY is set
- **Check**: Directories (chroma_db, uploads, logs) are writable
- **Check**: Port 8000 is not in use

### Slow queries
- **Reduce** top_k parameter
- **Use** dense mode instead of hybrid
- **Filter** by specific doc_id

### Out of memory
- **Clear** old documents with DELETE endpoint
- **Reduce** chunk size in preprocessing
- **Use** persistent ChromaDB with external storage

### Invalid API key
- **Verify**: OPENAI_API_KEY is correct and active
- **Check**: API key has necessary permissions
- **Test**: Key with direct OpenAI API

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)

---

## 🔄 API Versioning

Current version: **1.0.0**

Version information available at:
```bash
curl http://localhost:8000/
```
