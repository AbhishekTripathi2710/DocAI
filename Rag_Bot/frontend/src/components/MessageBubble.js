/**
 * Message Bubble Component
 * Displays individual chat messages with different styles for user/assistant
 */

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Chip,
  Collapse,
  IconButton,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import KeyboardArrowDownRoundedIcon from '@mui/icons-material/KeyboardArrowDownRounded';
import SourceRoundedIcon from '@mui/icons-material/SourceRounded';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const BubbleWrapper = styled(Box)(({ isUser }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: isUser ? 'flex-end' : 'flex-start',
  width: '100%',
  marginBottom: '16px',
}));

const Bubble = styled(Box)(({ theme, isUser }) => ({
  maxWidth: '85%',
  padding: '12px 20px',
  borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
  backgroundColor: isUser ? theme.palette.primary.main : '#1F2937',
  color: isUser ? '#FFFFFF' : theme.palette.text.primary,
  boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
  wordBreak: 'break-word',
  fontSize: '0.92rem',
  lineHeight: 1.6,

  // Markdown Styling
  '& p': { margin: 0 },
  '& p + p': { marginTop: '12px' },
  '& ul, & ol': { margin: '8px 0', paddingLeft: '24px' },
  '& li': { marginBottom: '4px' },
  '& table': {
    width: '100%',
    borderCollapse: 'collapse',
    margin: '16px 0',
    fontSize: '0.85rem',
    overflowX: 'auto',
    display: 'block',
    borderRadius: '8px',
    border: '1px solid rgba(255,255,255,0.1)',
  },
  '& th': {
    background: 'rgba(255,255,255,0.05)',
    padding: '10px 12px',
    textAlign: 'left',
    fontWeight: 600,
    borderBottom: '2px solid rgba(255,255,255,0.1)',
  },
  '& td': {
    padding: '8px 12px',
    borderBottom: '1px solid rgba(255,255,255,0.05)',
  },
  '& tr:last-child td': {
    borderBottom: 'none',
  },
  '& code': {
    background: 'rgba(0,0,0,0.3)',
    padding: '2px 6px',
    borderRadius: '4px',
    fontFamily: 'monospace',
    fontSize: '0.85rem',
  },
}));

const SourceCard = styled(Box)(({ theme }) => ({
  background: '#111827',
  border: '1px solid rgba(255,255,255,0.05)',
  borderRadius: '8px',
  padding: '12px',
  marginTop: '8px',
  transition: 'background 0.2s',
  '&:hover': {
    background: '#1F2937',
  },
}));

const ExpandButton = styled(Box)(({ theme, expanded }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: '4px',
  padding: '4px 8px',
  borderRadius: '6px',
  cursor: 'pointer',
  color: theme.palette.text.secondary,
  fontSize: '0.8rem',
  fontWeight: 500,
  userSelect: 'none',
  transition: 'all 0.2s',
  '&:hover': {
    color: theme.palette.text.primary,
    background: 'rgba(255,255,255,0.05)',
  },
  '& svg': {
    fontSize: '1.1rem',
    transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
    transition: 'transform 0.2s',
  },
}));

const MessageBubble = ({ message }) => {
  const [expanded, setExpanded] = useState(false);
  const isUser = message.type === 'user';

  return (
    <BubbleWrapper isUser={isUser}>
      <Bubble isUser={isUser}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {message.text}
        </ReactMarkdown>

        {/* Error message */}
        {message.error && (
          <Typography variant="caption" sx={{ color: '#EF4444', display: 'block', mt: 1, fontWeight: 500 }}>
            Error: {message.error}
          </Typography>
        )}
      </Bubble>

      {/* Metadata / Sources (Assistant only) */}
      {!isUser && (message.chunks || message.processingTime) && (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', mt: 1, ml: 1, maxWidth: '75%' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {message.chunks && message.chunks.length > 0 && (
              <ExpandButton expanded={expanded} onClick={() => setExpanded(!expanded)}>
                <SourceRoundedIcon sx={{ fontSize: '1rem !important' }} />
                {message.chunks.length} Sources
                <KeyboardArrowDownRoundedIcon />
              </ExpandButton>
            )}
            {message.processingTime && (
              <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.75rem' }}>
                {message.processingTime}ms
              </Typography>
            )}
          </Box>

          {message.chunks && message.chunks.length > 0 && (
            <Collapse in={expanded} timeout="auto" sx={{ width: '100%', mt: expanded ? 1 : 0 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {message.chunks.map((chunk, idx) => (
                  <SourceCard key={idx}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                        Source {idx + 1}
                      </Typography>
                      {chunk.score && (
                        <Typography variant="caption" sx={{ color: 'primary.light', fontWeight: 500 }}>
                          Match: {(chunk.score * 100).toFixed(0)}%
                        </Typography>
                      )}
                    </Box>
                    <Typography variant="body2" sx={{ color: 'text.primary', fontSize: '0.8rem', opacity: 0.9, fontStyle: 'italic', mb: 1 }}>
                      "{chunk.text.length > 200 ? chunk.text.substring(0, 200) + '...' : chunk.text}"
                    </Typography>
                    {chunk.metadata && Object.keys(chunk.metadata).length > 0 && (
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {chunk.metadata.page && (
                          <Chip label={`Page ${chunk.metadata.page}`} size="small" sx={{ height: 20, fontSize: '0.7rem', background: 'rgba(255,255,255,0.1)' }} />
                        )}
                        {chunk.metadata.type && (
                          <Chip label={chunk.metadata.type} size="small" sx={{ height: 20, fontSize: '0.7rem', background: 'rgba(255,255,255,0.1)' }} />
                        )}
                      </Box>
                    )}
                  </SourceCard>
                ))}
              </Box>
            </Collapse>
          )}
        </Box>
      )}
    </BubbleWrapper>
  );
};

export default MessageBubble;
