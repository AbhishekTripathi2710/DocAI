# 🚀 Quick Start Guide - RAG Bot FastAPI Backend

Get your RAG Bot API up and running in minutes!

---

## ⚡ 5-Minute Setup

### Step 1: Install Dependencies

```bash
# Install API dependencies
pip install -r requirements-api.txt

# Or install everything including RAG pipeline
pip install -r requirements.txt
pip install -r requirements-api.txt
```

### Step 2: Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your OpenAI API key
# On Windows: notepad .env
# On Mac/Linux: nano .env
```

**Minimum required:**
```
OPENAI_API_KEY=sk-your-api-key-here
```

### Step 3: Start the Server

**On Linux/Mac:**
```bash
chmod +x start_api.sh
./start_api.sh
```

**On Windows:**
```bash
start_api.bat
```

**Or directly with uvicorn:**
```bash
cd src
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Verify It's Running

```bash
# In another terminal, test the API
curl http://localhost:8000/ping

# Or open in browser
# API Docs: http://localhost:8000/docs
# Health: http://localhost:8000/health
```

---

## 📁 Complete Workflow

### 1. Upload a PDF

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -F "file=@sample.pdf"
```

**Response:**
```json
{
  "doc_id": "doc_abc123",
  "file_name": "sample.pdf",
  "pages": 10,
  "chunks_count": 95,
  "created_at": "2024-01-15T10:30:45",
  "document_type": "bank_statement"
}
```

### 2. Query the Document

```bash
curl -X POST "http://localhost:8000/query/hybrid" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the total amount?",
    "top_k": 3
  }'
```

**Response:**
```json
{
  "query": "What is the total amount?",
  "answer": "The total amount is $5,000.00",
  "retrieved_chunks": [
    {
      "text": "Total Amount: $5,000.00",
      "metadata": {"page": 1},
      "type": "key_value",
      "score": 0.95
    }
  ],
  "retrieval_mode": "hybrid",
  "processing_time_ms": 245.32
}
```

### 3. List Documents

```bash
curl "http://localhost:8000/documents/"
```

### 4. Delete Document

```bash
curl -X DELETE "http://localhost:8000/documents/doc_abc123"
```

---

## 🎯 Interactive API Testing

Open your browser to: **http://localhost:8000/docs**

You'll see the interactive Swagger UI where you can:
- ✅ Test all endpoints
- ✅ See request/response schemas
- ✅ View parameters and defaults
- ✅ Get real-time feedback

---

## 🔧 Common Tasks

### Change LLM Model

```bash
# Edit .env
export LLM_MODEL=gpt-4

# Restart the server
```

### Use Different Embedding Model

```bash
# Edit .env - for faster, lightweight model:
export EMBEDDING_MODEL=all-MiniLM-L6-v2

# Or for better quality:
export EMBEDDING_MODEL=all-mpnet-base-v2
```

### Enable Debug Logging

```bash
# Edit .env
export LOG_LEVEL=DEBUG

# Restart server - more detailed logs will appear
```

### Store Data Persistently

```bash
# Data is automatically persisted in:
./chroma_db/          # Vector embeddings
./bm25_index/         # Keyword index
./uploads/            # Uploaded PDFs
./metadata.json       # Document metadata
```

---

## 🐛 Troubleshooting

### ❌ "OPENAI_API_KEY not set"

**Solution:** Check your .env file
```bash
cat .env | grep OPENAI_API_KEY
# If empty, add your key:
echo 'OPENAI_API_KEY=sk-...' >> .env
```

### ❌ "Port 8000 already in use"

**Solution:** Use a different port
```bash
# Linux/Mac
uvicorn api.main:app --port 8001

# Or kill the process using port 8000
lsof -i :8000
kill -9 <PID>
```

### ❌ "ModuleNotFoundError"

**Solution:** Make sure you're in the right directory
```bash
cd src
uvicorn api.main:app --reload
```

### ❌ Slow Responses

**Solution:** Reduce complexity
- Use `top_k=3` instead of `top_k=10`
- Use `dense` mode instead of `hybrid`
- Query specific document with `doc_id`

### ❌ Out of Memory

**Solution:** Clear old data
```bash
# Delete a document
curl -X DELETE "http://localhost:8000/documents/{doc_id}"

# Or clear all data (warning: destructive)
rm -rf ./chroma_db ./bm25_index ./uploads ./metadata.json
```

---

## 📊 API Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check system status |
| `/ping` | GET | Quick health check |
| `/documents/upload` | POST | Upload PDF |
| `/documents/` | GET | List documents |
| `/documents/{id}` | GET | Get document info |
| `/documents/{id}` | DELETE | Delete document |
| `/query/dense` | POST | Semantic search |
| `/query/hybrid` | POST | Hybrid search (recommended) |
| `/query/ask` | POST | Auto-select retrieval |
| `/query/search` | GET | Simple search |

---

## 💡 Example Python Client

```python
import requests

BASE_URL = "http://localhost:8000"

# Upload document
with open("document.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/documents/upload",
        files={"file": f}
    )
    doc = response.json()
    print(f"Uploaded: {doc['doc_id']}")

# Ask question
response = requests.post(
    f"{BASE_URL}/query/hybrid",
    json={"query": "What's the total?"}
)
result = response.json()
print(f"Answer: {result['answer']}")

# List documents
response = requests.get(f"{BASE_URL}/documents/")
docs = response.json()
print(f"Total docs: {docs['total']}")
```

---

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f rag-api

# Stop
docker-compose down
```

---

## 🚀 Production Checklist

- [ ] Set up `.env` with production values
- [ ] Use strong `OPENAI_API_KEY`
- [ ] Enable HTTPS/SSL
- [ ] Set up persistent volume for `./data`
- [ ] Configure `LOG_LEVEL=WARNING`
- [ ] Set up monitoring/alerts
- [ ] Use multi-worker deployment
- [ ] Configure rate limiting
- [ ] Set up backups for metadata

---

## 📚 Learn More

- **Full API Docs**: See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Architecture**: See [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md)
- **RAG Pipeline**: See [README.md](README.md)
- **FastAPI**: https://fastapi.tiangolo.com/
- **ChromaDB**: https://docs.trychroma.com/

---

## 🆘 Need Help?

### Check Logs
```bash
tail -f logs/api.log
```

### Test Connectivity
```bash
curl -v http://localhost:8000/ping
```

### Verify Configuration
```bash
# Inside Python interpreter
import os
print(os.getenv('OPENAI_API_KEY'))
```

### View System Status
```bash
curl http://localhost:8000/health | python -m json.tool
```

---

## ✅ You're All Set!

Your RAG Bot API is running and ready to process documents and answer questions!

**Next steps:**
1. Upload a PDF document
2. Ask questions about its content
3. Integrate with your frontend
4. Scale to production

Happy RAG-ing! 🚀
