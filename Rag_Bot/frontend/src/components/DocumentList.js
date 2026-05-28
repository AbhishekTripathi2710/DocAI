/**
 * Document List Component
 * Displays list of uploaded documents with management options
 */

import React from 'react';
import {
  Box,
  IconButton,
  Typography,
  CircularProgress,
  Tooltip
} from '@mui/material';
import { styled } from '@mui/material/styles';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import InsertDriveFileOutlinedIcon from '@mui/icons-material/InsertDriveFileOutlined';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import { formatTimestamp } from '../utils/helpers';

const DocItem = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '12px',
  background: '#1F2937',
  borderRadius: '8px',
  border: '1px solid rgba(255,255,255,0.05)',
  marginBottom: '8px',
  transition: 'background 0.2s',
  '&:hover': {
    background: 'rgba(255,255,255,0.05)',
  },
}));

const DocumentList = ({ documents, loading = false, onDelete }) => {
  if (loading) {
    return (
      <Box sx={{ p: 2, textAlign: 'center' }}>
        <Typography color="text.secondary" variant="body2">Loading documents...</Typography>
      </Box>
    );
  }

  if (!documents || documents.length === 0) {
    return null;
  }

  return (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.5px', fontSize: '0.75rem' }}>
        Your Documents
      </Typography>
      
      <Box sx={{ display: 'flex', flexDirection: 'column' }}>
        {documents.map((doc) => (
          <DocItem key={doc.doc_id} sx={{ opacity: doc.status === 'failed' ? 0.7 : 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, overflow: 'hidden', flex: 1 }}>
              <InsertDriveFileOutlinedIcon sx={{ color: doc.status === 'failed' ? '#EF4444' : 'text.secondary', fontSize: '1.2rem' }} />
              <Box sx={{ overflow: 'hidden', flex: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 500, color: 'text.primary', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {doc.file_name}
                </Typography>
                
                {doc.status === 'processing' ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                    <CircularProgress size={10} thickness={6} color="primary" />
                    <Typography variant="caption" sx={{ color: 'primary.main', fontWeight: 500 }}>
                      Processing AI chunks...
                    </Typography>
                  </Box>
                ) : doc.status === 'failed' ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                    <ErrorOutlineIcon sx={{ fontSize: '0.85rem', color: '#EF4444' }} />
                    <Typography variant="caption" sx={{ color: '#EF4444' }}>
                      Processing failed
                    </Typography>
                  </Box>
                ) : (
                  <Typography variant="caption" sx={{ color: 'text.secondary', display: 'flex', gap: 1 }}>
                    <span>{doc.pages} pages</span>
                    <span>&bull;</span>
                    <span>{doc.chunks_count} chunks</span>
                  </Typography>
                )}
              </Box>
            </Box>
            
            {onDelete && (
              <IconButton
                size="small"
                onClick={() => onDelete(doc.doc_id)}
                disabled={doc.status === 'processing'}
                sx={{ 
                  color: 'text.secondary', 
                  ml: 1,
                  '&:hover': { color: '#EF4444', background: 'rgba(239, 68, 68, 0.1)' },
                  '&.Mui-disabled': { opacity: 0.3 }
                }}
              >
                <DeleteOutlineRoundedIcon fontSize="small" />
              </IconButton>
            )}
          </DocItem>
        ))}
      </Box>
    </Box>
  );
};

export default DocumentList;
