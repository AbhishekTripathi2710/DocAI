/**
 * API Configuration and Service
 * Handles all communication with the RAG Bot backend
 */

import axios from 'axios';

// API Configuration
// Support both process.env (Webpack) and fallback to localhost
const getApiBaseUrl = () => {
  try {
    if (typeof process !== 'undefined' && process.env && process.env.REACT_APP_API_URL) {
      return process.env.REACT_APP_API_URL;
    }
  } catch (e) {
    // process is not defined
  }
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * API Service Object
 * Contains all backend API calls
 */
const ApiService = {
  // Health & Status
  health: async () => {
    try {
      const response = await apiClient.get('/health');
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  },

  ping: async () => {
    try {
      const response = await apiClient.get('/ping');
      return response.data;
    } catch (error) {
      console.error('Ping failed:', error);
      throw error;
    }
  },

  // Document Management
  uploadDocument: async (file, docType) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('doc_type', docType);

      const response = await apiClient.post('/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Document upload failed:', error);
      throw error;
    }
  },

  listDocuments: async () => {
    try {
      const response = await apiClient.get('/documents/');
      return response.data;
    } catch (error) {
      console.error('Failed to list documents:', error);
      throw error;
    }
  },

  getDocument: async (docId) => {
    try {
      const response = await apiClient.get(`/documents/${docId}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to get document ${docId}:`, error);
      throw error;
    }
  },

  deleteDocument: async (docId) => {
    try {
      const response = await apiClient.delete(`/documents/${docId}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to delete document ${docId}:`, error);
      throw error;
    }
  },

  getDocumentStatus: async (docId) => {
    try {
      const response = await apiClient.get(`/documents/status/${docId}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to get status for document ${docId}:`, error);
      throw error;
    }
  },

  // Query & Retrieval
  queryDense: async (query, docId = null, topK = 5, includeMetadata = true) => {
    try {
      const response = await apiClient.post('/query/dense', {
        query,
        doc_id: docId,
        top_k: topK,
        include_metadata: includeMetadata,
      });
      return response.data;
    } catch (error) {
      console.error('Dense query failed:', error);
      throw error;
    }
  },

  queryHybrid: async (query, docId = null, topK = 5, includeMetadata = true) => {
    try {
      const response = await apiClient.post('/query/hybrid', {
        query,
        doc_id: docId,
        top_k: topK,
        include_metadata: includeMetadata,
      });
      return response.data;
    } catch (error) {
      console.error('Hybrid query failed:', error);
      throw error;
    }
  },

  ask: async (query, mode = 'hybrid', docId = null, topK = 10, llmProvider = 'ollama', docIds = null) => {
    try {
      const response = await apiClient.post('/query/ask', {
        query,
        mode,
        doc_id: docId,
        doc_ids: docIds,
        top_k: topK,
        llm_provider: llmProvider,
      });
      return response.data;
    } catch (error) {
      console.error('Ask query failed:', error);
      throw error;
    }
  },

  search: async (query, docId = null, topK = 10, mode = 'hybrid') => {
    try {
      const response = await apiClient.get('/query/search', {
        params: {
          q: query,
          doc_id: docId,
          top_k: topK,
          mode,
        },
      });
      return response.data;
    } catch (error) {
      console.error('Search failed:', error);
      throw error;
    }
  },
};

export default ApiService;
