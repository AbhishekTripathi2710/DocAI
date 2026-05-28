/**
 * Utilities for formatting and processing data
 */

/**
 * Format timestamp to readable format
 */
export const formatTimestamp = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleString();
};

/**
 * Format file size to human readable format
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
};

/**
 * Truncate text to specified length
 */
export const truncateText = (text, length = 100) => {
  if (!text) return '';
  if (text.length <= length) return text;
  return text.substring(0, length) + '...';
};

/**
 * Extract text from metadata
 */
export const extractMetadataText = (metadata) => {
  if (!metadata) return '';
  const parts = [];
  
  if (metadata.page) parts.push(`Page ${metadata.page}`);
  if (metadata.type) parts.push(`Type: ${metadata.type}`);
  if (metadata.document_type) parts.push(`Doc: ${metadata.document_type}`);
  
  return parts.join(' | ');
};

/**
 * Format document info for display
 */
export const formatDocumentInfo = (doc) => {
  return {
    id: doc.doc_id,
    name: doc.file_name,
    pages: doc.pages,
    chunks: doc.chunks_count,
    type: doc.document_type || 'Unknown',
    createdAt: formatTimestamp(doc.created_at),
  };
};

/**
 * Format query response for display
 */
export const formatQueryResponse = (response) => {
  return {
    query: response.query,
    answer: response.answer,
    chunks: response.retrieved_chunks || [],
    mode: response.retrieval_mode,
    time: response.processing_time_ms,
    chunksCount: response.retrieved_chunks?.length || 0,
  };
};

/**
 * Generate unique ID
 */
export const generateId = () => {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};
