/**
 * Document Upload Component
 * Handles PDF file upload with drag-and-drop support
 */

import React, { useRef, useState } from 'react';
import {
  Box,
  Button,
  CircularProgress,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined';
import ReceiptIcon from '@mui/icons-material/Receipt';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import ArticleIcon from '@mui/icons-material/Article';
import GavelIcon from '@mui/icons-material/Gavel';

const UploadZone = styled(Box)(({ theme, isDragActive }) => ({
  border: `1px dashed ${isDragActive ? theme.palette.primary.main : 'rgba(255,255,255,0.2)'}`,
  borderRadius: '12px',
  padding: '24px 16px',
  textAlign: 'center',
  cursor: 'pointer',
  transition: 'all 0.2s',
  backgroundColor: isDragActive ? 'rgba(99, 102, 241, 0.05)' : '#1F2937',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  '&:hover': {
    borderColor: theme.palette.primary.main,
    backgroundColor: 'rgba(99, 102, 241, 0.05)',
  },
}));

const DocTypeButton = styled(Button)(({ theme, active }) => ({
  flex: '1 1 calc(50% - 8px)',
  justifyContent: 'flex-start',
  padding: '12px 16px',
  backgroundColor: active ? 'rgba(99, 102, 241, 0.15)' : '#1F2937',
  border: `1px solid ${active ? theme.palette.primary.main : 'rgba(255, 255, 255, 0.05)'}`,
  borderRadius: '10px',
  color: active ? theme.palette.primary.main : theme.palette.text.secondary,
  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    backgroundColor: 'rgba(99, 102, 241, 0.08)',
    borderColor: theme.palette.primary.main,
    transform: 'translateY(-1px)',
  },
  '& .MuiButton-startIcon': {
    color: active ? theme.palette.primary.main : theme.palette.text.secondary,
    marginRight: '12px',
  },
}));

const DocumentUpload = ({ onUpload, loading = false }) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const [selectedDocType, setSelectedDocType] = useState(null);
  const fileInputRef = useRef(null);

  const docTypes = [
    { id: 'invoice', label: 'Invoice', icon: <ReceiptIcon /> },
    { id: 'bank_statement', label: 'Bank Statement', icon: <AccountBalanceIcon /> },
    { id: 'research_paper', label: 'Research Paper', icon: <ArticleIcon /> },
    { id: 'legal_document', label: 'Legal Document', icon: <GavelIcon /> },
  ];

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    
    if (!selectedDocType) {
      alert('Please select a document type first');
      return;
    }

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFileInput = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleUploadClick = () => {
    if (!selectedDocType) {
      alert('Please select a document type first');
      return;
    }
    fileInputRef.current?.click();
  };

  const handleFile = (file) => {
    if (file.type !== 'application/pdf') {
      alert('Please upload a PDF file');
      return;
    }
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      alert('File size exceeds 50MB limit');
      return;
    }
    onUpload(file, selectedDocType);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.5px', fontSize: '0.75rem' }}>
          1. Select Document Type
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5 }}>
          {docTypes.map((type) => (
            <DocTypeButton
              key={type.id}
              active={selectedDocType === type.id ? 1 : 0}
              onClick={() => setSelectedDocType(type.id)}
              startIcon={type.icon}
              variant="outlined"
              size="small"
              disabled={loading}
            >
              <Typography variant="body2" sx={{ fontWeight: selectedDocType === type.id ? 600 : 400 }}>
                {type.label}
              </Typography>
            </DocTypeButton>
          ))}
        </Box>
      </Box>

      <Box>
        <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.5px', fontSize: '0.75rem', opacity: selectedDocType ? 1 : 0.5 }}>
          2. Upload File
        </Typography>
        <UploadZone
          isDragActive={isDragActive}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => !loading && handleUploadClick()}
          sx={{ 
            opacity: selectedDocType ? 1 : 0.5,
            pointerEvents: loading ? 'none' : 'auto',
            borderStyle: selectedDocType ? 'dashed' : 'solid',
            borderColor: selectedDocType ? 'primary.main' : 'rgba(255,255,255,0.1)'
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileInput}
            style={{ display: 'none' }}
            disabled={loading || !selectedDocType}
          />

          {loading ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
              <CircularProgress size={24} thickness={4} />
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                Processing document...
              </Typography>
            </Box>
          ) : (
            <>
              <CloudUploadOutlinedIcon sx={{ fontSize: 32, color: selectedDocType ? 'primary.main' : 'text.disabled', mb: 1, opacity: 0.8 }} />
              <Typography variant="body2" sx={{ fontWeight: 500, color: selectedDocType ? 'text.primary' : 'text.disabled', mb: 0.5 }}>
                {selectedDocType ? 'Click or drag PDF here' : 'Select type first'}
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.disabled' }}>
                Up to 50MB
              </Typography>
            </>
          )}
        </UploadZone>
      </Box>
    </Box>
  );
};

export default DocumentUpload;
