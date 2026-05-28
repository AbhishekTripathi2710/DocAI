/**
 * Main App Component
 * Orchestrates the entire RAG chatbot application
 */

import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Drawer,
  IconButton,
  List,
  ListItem,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import MenuIcon from '@mui/icons-material/Menu';
import CloseIcon from '@mui/icons-material/Close';

import ChatInterface from './components/ChatInterface';
import DocumentUpload from './components/DocumentUpload';
import DocumentList from './components/DocumentList';
import RetrievalOptions from './components/RetrievalOptions';
import ApiService from './services/ApiService';
import { generateId, formatQueryResponse } from './utils/helpers';

// Create modern dark theme
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#6366F1', // Indigo/Purple accent
      light: '#818CF8',
      dark: '#4F46E5',
    },
    background: {
      default: '#0B0F14', // Deep black/blue
      paper: '#111827', // Soft gray/black surface
    },
    text: {
      primary: '#F9FAFB',
      secondary: '#9CA3AF',
    },
    divider: 'rgba(255, 255, 255, 0.08)',
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    button: {
      textTransform: 'none',
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
  },
});

const DRAWER_WIDTH = 320;

function App() {
  const [messages, setMessages] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [apiHealth, setApiHealth] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [queryOptions, setQueryOptions] = useState({
    mode: 'hybrid',
    topK: 10,
    selectedDocId: null,
    includeMetadata: true,
    llmProvider: 'ollama',
    documents: [],
  });

  useEffect(() => {
    initializeApp();
  }, []);

  useEffect(() => {
    setQueryOptions((prev) => ({ ...prev, documents }));
  }, [documents]);

  const initializeApp = async () => {
    try {
      const health = await ApiService.health();
      setApiHealth(health);
      await loadDocuments();
      setError(null);
    } catch (err) {
      console.error('Initialization failed:', err);
      setError('Failed to connect to backend API.');
    }
  };

  const loadDocuments = async () => {
    try {
      const response = await ApiService.listDocuments();
      setDocuments(response.documents || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const handleDocumentUpload = async (file, docType) => {
    setUploading(true);
    setError(null);
    try {
      const response = await ApiService.uploadDocument(file, docType);
      const docId = response.doc_id;
      
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          type: 'system',
          text: `Document "${response.file_name}" is being processed in the background.`,
        },
      ]);
      
      // Refresh list to show 'processing' state
      await loadDocuments();
      setUploading(false); // Can stop 'uploading' spinner now that server accepted it

      // Start polling for completion
      pollDocumentStatus(docId);
      
    } catch (err) {
      console.error('Upload failed:', err);
      let errorMsg = err.response?.data?.detail || err.message || 'Upload failed';
      if (typeof errorMsg === 'object') {
        errorMsg = JSON.stringify(errorMsg, null, 2);
      }
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          type: 'error',
          text: `Upload failed: ${errorMsg}`,
          error: errorMsg,
        },
      ]);
      setError(`Upload failed: ${errorMsg}`);
      setUploading(false);
    }
  };

  const pollDocumentStatus = async (docId) => {
    const poll = async () => {
      try {
        const statusResponse = await ApiService.getDocumentStatus(docId);
        
        // Update documents list with latest status
        setDocuments(prev => prev.map(doc => 
          doc.doc_id === docId ? { ...doc, ...statusResponse } : doc
        ));

        if (statusResponse.status === 'processing') {
          setTimeout(poll, 5000); // Check again in 5 seconds
        } else if (statusResponse.status === 'completed') {
          setMessages((prev) => [
            ...prev,
            {
              id: generateId(),
              type: 'system',
              text: `Document "${statusResponse.file_name}" is ready for querying.`,
            },
          ]);
        } else if (statusResponse.status === 'failed') {
          setMessages((prev) => [
            ...prev,
            {
              id: generateId(),
              type: 'error',
              text: `Processing failed for "${statusResponse.file_name}". Check server logs.`,
            },
          ]);
        }
      } catch (err) {
        console.error(`Status poll failed for ${docId}:`, err);
      }
    };
    
    // Start the first poll after 5 seconds
    setTimeout(poll, 5000);
  };

  const handleSendMessage = async (query, targetDocIds = null) => {
    const userMessage = { id: generateId(), type: 'user', text: query };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setError(null);

    let docId = null;
    let docIds = null;

    if (targetDocIds) {
      if (Array.isArray(targetDocIds)) {
        docIds = targetDocIds;
      } else {
        docId = targetDocIds;
      }
    } else {
      docId = queryOptions.selectedDocId || null;
    }

    try {
      const response = await ApiService.ask(
        query,
        queryOptions.mode || 'hybrid',
        docId,
        queryOptions.topK || 10,
        queryOptions.llmProvider || 'ollama',
        docIds
      );
      const formattedResponse = formatQueryResponse(response);
      const assistantMessage = {
        id: generateId(),
        type: 'assistant',
        text: formattedResponse.answer,
        chunks: formattedResponse.chunks,
        processingTime: formattedResponse.time,
        mode: formattedResponse.mode,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Query failed:', err);
      let errorMsg = err.response?.data?.detail || err.message || 'Query failed';
      if (typeof errorMsg === 'object') {
        errorMsg = JSON.stringify(errorMsg, null, 2);
      }
      const errorMessage = {
        id: generateId(),
        type: 'assistant',
        text: `Error processing query: ${errorMsg}`,
        error: errorMsg,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDocument = async (docId) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      await ApiService.deleteDocument(docId);
      await loadDocuments();
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          type: 'system',
          text: 'Document deleted successfully',
        },
      ]);
    } catch (err) {
      console.error('Delete failed:', err);
      setError(`Delete failed: ${err.message}`);
    }
  };

  const handleClearMessages = () => setMessages([]);
  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);

  const sidebarContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', p: 3, gap: 3 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: '-0.5px' }}>
        RAG AI
      </Typography>

      {apiHealth && (
        <Alert severity={apiHealth.status === 'healthy' ? 'success' : 'warning'} sx={{ borderRadius: 2 }}>
          {apiHealth.status === 'healthy' ? 'System Online' : 'System Degraded'}
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ borderRadius: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, flex: 1 }}>
        <DocumentUpload onUpload={handleDocumentUpload} loading={uploading} />
        <DocumentList documents={documents} loading={false} onDelete={handleDeleteDocument} />
        <RetrievalOptions options={queryOptions} onOptionsChange={setQueryOptions} disabled={loading} />
      </Box>
    </Box>
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>

        {/* Mobile App Bar / Menu Icon */}
        {isMobile && (
          <Box sx={{ position: 'absolute', top: 16, left: 16, zIndex: 1200 }}>
            <IconButton onClick={handleDrawerToggle} color="inherit">
              <MenuIcon />
            </IconButton>
          </Box>
        )}

        {/* Sidebar */}
        <Drawer
          variant={isMobile ? 'temporary' : 'permanent'}
          open={isMobile ? mobileOpen : true}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            width: DRAWER_WIDTH,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: DRAWER_WIDTH,
              boxSizing: 'border-box',
              borderRight: '1px solid rgba(255,255,255,0.05)',
              backgroundColor: '#0B0F14',
            },
          }}
        >
          {sidebarContent}
        </Drawer>

        {/* Main Chat Area */}
        <Box component="main" sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', backgroundColor: '#111827' }}>
          <ChatInterface
            messages={messages}
            loading={loading}
            onSendMessage={handleSendMessage}
            onClearMessages={handleClearMessages}
            disabled={documents.length === 0}
            documents={documents}
          />
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
