/**
 * Retrieval Options Component
 * Allows users to configure query parameters
 */

import React from 'react';
import {
  Box,
  FormControl,
  FormControlLabel,
  MenuItem,
  Select,
  Slider,
  Switch,
  Typography,
} from '@mui/material';

const RetrievalOptions = ({ options, onOptionsChange, disabled = false }) => {
  const handleModeChange = (event) => {
    onOptionsChange({ ...options, mode: event.target.value });
  };

  const handleTopKChange = (event, value) => {
    onOptionsChange({ ...options, topK: value });
  };

  const handleDocIdChange = (event) => {
    onOptionsChange({ ...options, selectedDocId: event.target.value });
  };

  const handleMetadataChange = (event) => {
    onOptionsChange({ ...options, includeMetadata: event.target.checked });
  };

  const handleProviderChange = (event) => {
    onOptionsChange({ ...options, llmProvider: event.target.value });
  };

  return (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.5px', fontSize: '0.75rem' }}>
        Settings
      </Typography>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
        {/* LLM Provider */}
        <Box>
          <Typography variant="caption" sx={{ color: 'text.secondary', mb: 0.5, display: 'block' }}>
            LLM Provider
          </Typography>
          <FormControl size="small" fullWidth disabled={disabled}>
            <Select 
              value={options.llmProvider || 'ollama'} 
              onChange={handleProviderChange}
              sx={{ 
                borderRadius: '8px', 
                fontSize: '0.85rem',
                backgroundColor: '#1F2937',
                '& fieldset': { border: '1px solid rgba(255,255,255,0.05)' },
              }}
            >
              <MenuItem value="ollama" sx={{ fontSize: '0.85rem' }}>Ollama (Llama 3 Local)</MenuItem>
              <MenuItem value="groq" sx={{ fontSize: '0.85rem' }}>Groq (Llama 3 Cloud)</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {/* Retrieval Mode */}
        {/* <Box>
          <Typography variant="caption" sx={{ color: 'text.secondary', mb: 0.5, display: 'block' }}>
            Retrieval Mode
          </Typography>
          <FormControl size="small" fullWidth disabled={disabled}>
            <Select 
              value={options.mode || 'hybrid'} 
              onChange={handleModeChange}
              sx={{ 
                borderRadius: '8px', 
                fontSize: '0.85rem',
                backgroundColor: '#1F2937',
                '& fieldset': { border: '1px solid rgba(255,255,255,0.05)' },
              }}
            >
              <MenuItem value="dense" sx={{ fontSize: '0.85rem' }}>Dense (Semantic)</MenuItem>
              <MenuItem value="hybrid" sx={{ fontSize: '0.85rem' }}>Hybrid (Recommended)</MenuItem>
            </Select>
          </FormControl>
        </Box> */}

        {/* Top K Results */}
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Top Results
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.primary', fontWeight: 500 }}>
              {options.topK || 10}
            </Typography>
          </Box>
          <Slider
            min={1}
            max={100}
            value={options.topK || 10}
            onChange={handleTopKChange}
            disabled={disabled}
            size="small"
            sx={{
              color: 'primary.main',
              '& .MuiSlider-thumb': { width: 14, height: 14 },
            }}
          />
        </Box>

        {/* Document Selection */}
        {options.documents && options.documents.length > 0 && (
          <Box>
            <Typography variant="caption" sx={{ color: 'text.secondary', mb: 0.5, display: 'block' }}>
              Search Context
            </Typography>
            <FormControl size="small" fullWidth disabled={disabled}>
              <Select
                value={options.selectedDocId || 'all'}
                onChange={handleDocIdChange}
                sx={{
                  borderRadius: '8px',
                  fontSize: '0.85rem',
                  backgroundColor: '#1F2937',
                  '& fieldset': { border: '1px solid rgba(255,255,255,0.05)' },
                }}
              >
                <MenuItem value="all" sx={{ fontSize: '0.85rem' }}>All Documents</MenuItem>
                {options.documents.map((doc) => (
                  <MenuItem key={doc.doc_id} value={doc.doc_id} sx={{ fontSize: '0.85rem' }}>
                    {doc.file_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        )}

        {/* Include Metadata */}
        <FormControlLabel
          control={
            <Switch
              checked={options.includeMetadata !== false}
              onChange={handleMetadataChange}
              disabled={disabled}
              size="small"
            />
          }
          label={<Typography variant="caption" sx={{ color: 'text.secondary' }}>Show Sources</Typography>}
          sx={{ m: 0 }}
        />
      </Box>
    </Box>
  );
};

export default RetrievalOptions;
