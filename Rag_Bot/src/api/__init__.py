"""
RAG Bot API Package

A REST API for Retrieval Augmented Generation over PDF documents.

Main modules:
- main.py: FastAPI application entry point
- models.py: Pydantic request/response schemas
- config.py: Configuration settings
- dependencies.py: Dependency injection and singleton instances
- utils.py: Utility functions
- routes/: API endpoint handlers
  - health.py: Health check endpoints
  - documents.py: Document management endpoints
  - retrieval.py: Query and retrieval endpoints
"""

__version__ = "1.0.0"
__author__ = "RAG Bot Team"
