# RAG Bot FastAPI Backend - Architecture Guide

## 🏗️ Backend Architecture

```
FastAPI Application
    ↓
├── models.py (Pydantic schemas)
├── config.py (Settings & configuration)
├── dependencies.py (Singleton instances & DI)
├── utils.py (Helper functions)
├── main.py (FastAPI app setup)
│
└── routes/
    ├── health.py (Health checks)
    ├── documents.py (Document management)
    └── retrieval.py (Query handling)
```

---

## 📦 Project Structure

```
src/
├── api/                          # FastAPI Backend
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # FastAPI application
│   ├── models.py                # Pydantic models
│   ├── config.py                # Configuration
│   ├── dependencies.py          # Dependency injection
│   ├── utils.py                 # Utilities
│   └── routes/                  # API endpoints
│       ├── __init__.py
│       ├── health.py            # Health checks
│       ├── documents.py         # Document CRUD
│       └── retrieval.py         # Query/RAG
│
├── embeddings/                   # Vector embeddings
│   ├── embedder.py              # Embeddings + ChromaDB
│   └── __init__.py
│
├── extraction/                   # PDF extraction
│   ├── pipeline.py              # Main extraction
│   ├── parser.py                # Configuration
│   ├── text_extractor.py        # Text extraction
│   ├── table_extractor.py       # Table extraction
│   ├── hybrid_retriever.py      # Hybrid search
│   ├── bm25_index.py            # BM25 indexing
│   └── __init__.py
│
├── preprocessing/               # Chunking
│   ├── chunker.py               # Text chunking
│   └── __init__.py
│
└── rag/                          # RAG chain
    ├── chain.py                 # RAG orchestration
    ├── prompt.py                # Prompt engineering
    └── __init__.py
```

---

## 🔌 API Endpoints Structure

### Health Endpoints
```
GET  /ping                          Health check (quick)
GET  /health                        System status
```

### Document Management
```
POST   /documents/upload            Upload PDF
GET    /documents/                  List documents
GET    /documents/{doc_id}          Get document info
DELETE /documents/{doc_id}          Delete document
```

### Query & Retrieval
```
POST /query/dense                   Dense retrieval query
POST /query/hybrid                  Hybrid retrieval query
POST /query/ask                     Auto mode selection
GET  /query/search                  Simple search (query params)
```

---

## 🔄 Data Flow - Document Upload

```
1. User uploads PDF (POST /documents/upload)
   ↓
2. Validate file (size, type)
   ↓
3. Save to disk (./uploads/{doc_id}/)
   ↓
4. Extract content (extraction/pipeline.py)
   ├── Extract text blocks
   ├── Extract tables
   └── Classify document type
   ↓
5. Preprocess chunks (preprocessing/chunker.py)
   ├── Merge small chunks
   ├── Convert tables to sentences/JSON
   └── Optimize for embedding
   ↓
6. Generate embeddings (embeddings/embedder.py)
   ├── SentenceTransformers embedding
   └── Store in ChromaDB
   ↓
7. Build BM25 index (extraction/bm25_index.py)
   └── Index chunk texts for keyword search
   ↓
8. Store metadata (dependencies.py)
   └── JSON metadata store
   ↓
9. Return document info (models.py → DocumentInfo)
```

---

## 🔄 Data Flow - Query

```
1. User sends query (POST /query/hybrid)
   ↓
2. Parse request (models.py → QueryRequest)
   ↓
3. Dense retrieval (embeddings/embedder.py)
   ├── Embed query with SentenceTransformers
   └── Search ChromaDB for similar chunks
   ↓
4. Sparse retrieval (extraction/bm25_index.py)
   ├── Tokenize query
   └── BM25 search for keyword matches
   ↓
5. Fuse results (extraction/hybrid_retriever.py)
   ├── Reciprocal Rank Fusion (RRF)
   └── Combine and rank results
   ↓
6. Generate answer (rag/chain.py)
   ├── Format context (rag/prompt.py)
   └── Call LLM with retrieved chunks
   ↓
7. Return results (models.py → QueryResponse)
```

---

## 🔐 Dependency Injection Pattern

### Singleton Instances

Located in `dependencies.py`:

```python
_embedder: ChunkEmbedder           # Embeddings manager
_bm25_index: BM25Index            # Keyword indexing
_retriever: HybridRetriever       # Hybrid search
_rag_chain: RAGChain              # Answer generation
_document_metadata: dict          # Document registry
```

### Usage in Routes

```python
from api.dependencies import get_embedder, get_rag_chain

async def query_dense(request: QueryRequest):
    embedder = get_embedder()      # Get singleton instance
    results = embedder.query(...)
```

**Benefits:**
- Single instance per application lifetime
- Efficient resource usage
- Thread-safe operations
- Easy to mock for testing

---

## ⚙️ Configuration Management

### Configuration Hierarchy

```
1. Environment Variables (.env file)
   ↓
2. config.py defaults
   ↓
3. API defaults
```

### Key Configuration

| Setting | Source | Default | Purpose |
|---------|--------|---------|---------|
| OPENAI_API_KEY | .env | Required | LLM authentication |
| EMBEDDING_MODEL | .env | all-MiniLM-L6-v2 | Embeddings |
| CHROMA_DB_PATH | .env | ./chroma_db | Vector storage |
| UPLOAD_DIR | .env | ./uploads | PDF storage |
| LOG_LEVEL | .env | INFO | Logging verbosity |

---

## 📊 Data Models

### Request Models (in models.py)

```
QueryRequest
├── query: str              # Search query
├── doc_id: Optional[str]   # Document filter
├── top_k: int              # Result count
├── mode: RetrievalMode     # Dense or hybrid
└── include_metadata: bool  # Include metadata

DocumentUploadRequest
└── file_name: str
```

### Response Models

```
QueryResponse
├── query: str
├── answer: str
├── retrieved_chunks: List[ChunkData]
├── retrieval_mode: str
└── processing_time_ms: float

DocumentInfo
├── doc_id: str
├── file_name: str
├── pages: int
├── chunks_count: int
├── created_at: str
└── document_type: str
```

---

## 🛠️ Middleware & Error Handling

### Middleware Pipeline

```
Request
  ↓
CORS Middleware (allow_origins)
  ↓
Logging Middleware (request/response logging)
  ↓
Route Handler
  ↓
Error Handler
  ↓
Response
```

### Error Handling

```python
# Global exception handler
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    # Standardized error response
    return {
        "error": "Error Type",
        "detail": "Message",
        "status_code": 500
    }
```

---

## 🚀 Startup Sequence

```
1. Application initialization
   └── lifespan context manager starts
   
2. Dependencies initialization
   ├── ChunkEmbedder (ChromaDB connection)
   ├── BM25Index (load from disk or create)
   ├── HybridRetriever (combine both)
   ├── RAGChain (LLM setup)
   └── Document metadata (load from JSON)

3. Routes registration
   ├── Health routes
   ├── Document routes
   └── Retrieval routes

4. Server listening
   └── Ready for requests
```

---

## 🔧 Extension Points

### Adding New Routes

1. Create route file in `routes/`
2. Define router and endpoints
3. Include in main.py:
   ```python
   app.include_router(new_routes.router)
   ```

### Adding New Models

1. Add Pydantic model in `models.py`
2. Use in routes with type hints
3. Automatic validation and docs

### Modifying Configuration

1. Add setting to `config.py`
2. Read from environment or use default
3. Import in other modules as needed

### Custom Middleware

1. Create middleware function
2. Add to app:
   ```python
   app.middleware("http")(my_middleware)
   ```

---

## 📈 Performance Optimization

### Caching Strategies

1. **Embedder caching**: ChromaDB handles persistence
2. **BM25 caching**: Index loaded in memory
3. **Metadata caching**: JSON loaded at startup
4. **Singleton pattern**: Reuse instances

### Request Optimization

1. **Top-k reduction**: Use smaller values for speed
2. **Retrieval mode**: Dense mode faster than hybrid
3. **Filtering**: Use doc_id to narrow search space
4. **Batch processing**: Queue multiple requests

### Resource Management

1. **Connection pooling**: OpenAI client managed
2. **Memory limits**: Chunk size optimization
3. **Storage**: Disk persistence for data
4. **Worker processes**: Multi-worker deployment

---

## 🔐 Security Considerations

### API Security

1. **Input validation**: Pydantic models validate all inputs
2. **Error messages**: Generic error messages in production
3. **Rate limiting**: Can be added with middleware
4. **CORS**: Configurable allowed origins
5. **Authentication**: Can be added with middleware

### Environment Security

1. **API Keys**: Loaded from .env, never in code
2. **Log sanitization**: Sensitive data not logged
3. **File permissions**: Secure upload directory
4. **Database**: ChromaDB in local directory

---

## 🧪 Testing Structure

Suggested test organization:

```
tests/
├── test_routes/
│   ├── test_health.py
│   ├── test_documents.py
│   └── test_retrieval.py
├── test_models.py
├── test_config.py
└── conftest.py (fixtures)
```

---

## 📚 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | FastAPI | REST API |
| Server | Uvicorn | ASGI server |
| Validation | Pydantic | Request validation |
| Embeddings | SentenceTransformers | Vector embeddings |
| Vector DB | ChromaDB | Similarity search |
| Keyword Search | rank-bm25 | Sparse retrieval |
| LLM | OpenAI API | Answer generation |
| Web Client | FastAPI docs | Interactive testing |

---

## 🔗 Integration Points

### With RAG Pipeline

- ✅ Uses all extraction modules
- ✅ Uses embedder for vectors
- ✅ Uses BM25 for sparse search
- ✅ Uses RAG chain for generation

### With External Services

- ✅ OpenAI API (LLM)
- ✅ ChromaDB (vector store)
- ✅ File system (uploads/logs)

### Can Integrate

- 🔄 Redis (caching)
- 🔄 PostgreSQL (persistent metadata)
- 🔄 Elasticsearch (advanced search)
- 🔄 Kafka (event streaming)

---

## 📝 Documentation

- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **This Guide**: Backend architecture overview
- **API_DOCUMENTATION.md**: Complete API reference

---

## 🚀 Deployment Options

### Local Development
```bash
./start_api.sh          # Linux/Mac
start_api.bat           # Windows
```

### Docker Deployment
```bash
docker-compose up       # With dependencies
```

### Production Deployment
```bash
uvicorn api.main:app --workers 4 --host 0.0.0.0 --port 8000
```

### Cloud Deployment
- Deploy docker image to AWS/GCP/Azure
- Set environment variables
- Mount data volumes for persistence
