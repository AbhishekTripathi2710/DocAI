/**
 * Chat Interface Component
 * Main chat window with message display and input
 */

import React, { useEffect, useRef } from 'react';
import {
  Box,
  IconButton,
  InputBase,
  Typography,
  Chip,
  ClickAwayListener,
} from '@mui/material';
import { styled, keyframes } from '@mui/material/styles';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import DescriptionRoundedIcon from '@mui/icons-material/DescriptionRounded';
import MessageBubble from './MessageBubble';

const ChatContainer = styled(Box)({
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  width: '100%',
  position: 'relative',
});

const MessagesArea = styled(Box)({
  flex: 1,
  overflowY: 'auto',
  padding: '24px',
  display: 'flex',
  flexDirection: 'column',
  gap: '24px',
  scrollBehavior: 'smooth',
  '&::-webkit-scrollbar': {
    width: '6px',
  },
  '&::-webkit-scrollbar-thumb': {
    background: 'rgba(255, 255, 255, 0.1)',
    borderRadius: '10px',
  },
  '&::-webkit-scrollbar-track': {
    background: 'transparent',
  },
});

const InputWrapper = styled(Box)(({ theme }) => ({
  position: 'sticky',
  bottom: 0,
  padding: '24px',
  background: 'linear-gradient(180deg, rgba(17,24,39,0) 0%, rgba(17,24,39,1) 40%)',
  display: 'flex',
  justifyContent: 'center',
  position: 'relative', // Relative anchor for mentions dropdown
}));

const InputBox = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  background: '#1F2937',
  borderRadius: '24px',
  padding: '8px 16px',
  width: '100%',
  maxWidth: '768px',
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  border: '1px solid rgba(255,255,255,0.05)',
  transition: 'all 0.2s',
  '&:focus-within': {
    borderColor: theme.palette.primary.main,
  },
}));

const StyledInputBase = styled(InputBase)(({ theme }) => ({
  color: theme.palette.text.primary,
  flex: 1,
  minWidth: '150px',
  padding: '4px 8px',
  fontSize: '0.95rem',
  '& .MuiInputBase-input': {
    maxHeight: '150px',
    overflowY: 'auto !important',
  },
}));

const MentionsDropdown = styled(Box)(({ theme }) => ({
  position: 'absolute',
  bottom: 'calc(100% - 8px)',
  width: 'calc(100% - 48px)',
  maxWidth: '768px',
  background: 'rgba(31, 41, 55, 0.95)',
  backdropFilter: 'blur(16px)',
  border: '1px solid rgba(255, 255, 255, 0.08)',
  borderRadius: '16px',
  boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.3)',
  zIndex: 1000,
  maxHeight: '240px',
  overflowY: 'auto',
  padding: '8px 0',
  '&::-webkit-scrollbar': {
    width: '6px',
  },
  '&::-webkit-scrollbar-thumb': {
    background: 'rgba(255, 255, 255, 0.1)',
    borderRadius: '10px',
  },
}));

const MentionItem = styled(Box)(({ theme }) => ({
  padding: '10px 16px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  color: theme.palette.text.primary,
  transition: 'all 0.2s',
  '&:hover': {
    background: 'rgba(99, 102, 241, 0.15)',
    color: '#818CF8',
  },
}));

const bounce = keyframes`
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
`;

const TypingIndicator = styled(Box)(({ theme }) => ({
  display: 'flex',
  gap: '4px',
  padding: '16px 20px',
  background: '#1F2937',
  borderRadius: '16px 16px 16px 4px',
  width: 'fit-content',
  alignItems: 'center',
  marginTop: '8px',
  '& span': {
    width: '6px',
    height: '6px',
    background: theme.palette.text.secondary,
    borderRadius: '50%',
    animation: `${bounce} 1.4s infinite ease-in-out both`,
  },
  '& span:nth-of-type(1)': { animationDelay: '-0.32s' },
  '& span:nth-of-type(2)': { animationDelay: '-0.16s' },
}));

const ChatInterface = ({
  messages,
  loading,
  onSendMessage,
  onClearMessages,
  disabled = false,
  documents = [],
}) => {
  const [inputValue, setInputValue] = React.useState('');
  const [selectedDocs, setSelectedDocs] = React.useState([]);
  const [showMentions, setShowMentions] = React.useState(false);
  const [mentionSearch, setMentionSearch] = React.useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = () => {
    if (!inputValue.trim() || disabled || loading) return;
    onSendMessage(inputValue, selectedDocs.length > 0 ? selectedDocs.map(d => d.doc_id) : null);
    setInputValue('');
    setSelectedDocs([]); // Clear search lock after message is sent
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInputValue(value);

    // Trigger mentions if user types '@' preceded by a space/newline or at the start
    const lastAtIndex = value.lastIndexOf('@');
    if (lastAtIndex !== -1) {
      const beforeChar = lastAtIndex > 0 ? value[lastAtIndex - 1] : ' ';
      if (beforeChar === ' ' || beforeChar === '\n') {
        const textAfterAt = value.substring(lastAtIndex + 1);
        // Only show mentions if there are no spaces in the search string after '@'
        if (!textAfterAt.includes(' ')) {
          setShowMentions(true);
          setMentionSearch(textAfterAt);
          return;
        }
      }
    }

    setShowMentions(false);
    setMentionSearch('');
  };

  const handleSelectDocument = (doc) => {
    setSelectedDocs((prev) => {
      if (prev.some((d) => d.doc_id === doc.doc_id)) {
        return prev;
      }
      return [...prev, doc];
    });
    setShowMentions(false);
    setMentionSearch('');

    // Remove the '@mentionsearch' part from the input
    const lastAtIndex = inputValue.lastIndexOf('@');
    if (lastAtIndex !== -1) {
      const newValue = inputValue.substring(0, lastAtIndex);
      setInputValue(newValue);
    }
  };

  // Filter completed documents based on mention search input
  const completedDocs = (documents || []).filter(doc => doc.status === 'completed');
  const filteredDocs = completedDocs.filter(doc =>
    doc.file_name.toLowerCase().includes(mentionSearch.toLowerCase())
  );

  return (
    <ChatContainer>
      {/* Top action bar (Clear Chat) */}
      {messages.length > 0 && (
        <Box sx={{ position: 'absolute', top: 16, right: 24, zIndex: 10 }}>
          <IconButton onClick={onClearMessages} disabled={loading} size="small" sx={{ color: 'text.secondary', '&:hover': { color: 'text.primary', background: 'rgba(255,255,255,0.05)' }}}>
            <DeleteOutlineRoundedIcon fontSize="small" />
          </IconButton>
        </Box>
      )}

      <MessagesArea>
        {messages.length === 0 ? (
          <Box sx={{ m: 'auto', textAlign: 'center', color: 'text.secondary', maxWidth: 400 }}>
            <Typography variant="h5" sx={{ fontWeight: 600, color: 'text.primary', mb: 2 }}>
              How can I help you?
            </Typography>
            <Typography variant="body2">
              Upload a document from the sidebar and ask me anything about its contents. I'll search and summarize the information for you.
            </Typography>
          </Box>
        ) : (
          messages.map((msg, idx) => (
            <MessageBubble key={idx} message={msg} />
          ))
        )}
        
        {loading && (
          <Box sx={{ display: 'flex' }}>
            <TypingIndicator>
              <span />
              <span />
              <span />
            </TypingIndicator>
          </Box>
        )}
        <div ref={messagesEndRef} />
      </MessagesArea>

      <InputWrapper>
        {/* Sleek Autocomplete Overlay Dropdown */}
        {showMentions && (
          <ClickAwayListener onClickAway={() => setShowMentions(false)}>
            <MentionsDropdown>
              <Box sx={{ px: 2, py: 1, borderBottom: '1px solid rgba(255, 255, 255, 0.05)', mb: 0.5 }}>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Target Specific Document Context
                </Typography>
              </Box>
              {filteredDocs.length === 0 ? (
                <Box sx={{ px: 2, py: 1.5, color: 'text.secondary' }}>
                  <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>
                    No completed documents found matching "{mentionSearch}"
                  </Typography>
                </Box>
              ) : (
                filteredDocs.map((doc) => (
                  <MentionItem key={doc.doc_id} onClick={() => handleSelectDocument(doc)}>
                    <DescriptionRoundedIcon sx={{ fontSize: '1.1rem', color: '#9CA3AF' }} />
                    <Box sx={{ flex: 1, overflow: 'hidden' }}>
                      <Typography variant="body2" sx={{ fontSize: '0.85rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {doc.file_name}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.72rem', display: 'block' }}>
                        {doc.pages} pages • {doc.chunks_count} chunks
                      </Typography>
                    </Box>
                  </MentionItem>
                ))
              )}
            </MentionsDropdown>
          </ClickAwayListener>
        )}

        <InputBox
          sx={{
            borderColor: selectedDocs.length > 0 ? 'primary.main' : 'rgba(255,255,255,0.05)',
            boxShadow: selectedDocs.length > 0 
              ? '0 0 14px rgba(99, 102, 241, 0.25), 0 4px 6px -1px rgba(0, 0, 0, 0.1)' 
              : '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          }}
        >
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: '6px 8px', flex: 1, alignItems: 'center' }}>
            {selectedDocs.map((doc) => (
              <Chip
                key={doc.doc_id}
                icon={<DescriptionRoundedIcon sx={{ fontSize: '1rem !important', color: '#818CF8 !important' }} />}
                label={doc.file_name.length > 25 ? `${doc.file_name.substring(0, 22)}...` : doc.file_name}
                onDelete={() => setSelectedDocs(prev => prev.filter(d => d.doc_id !== doc.doc_id))}
                color="primary"
                variant="outlined"
                sx={{
                  background: 'rgba(99, 102, 241, 0.1)',
                  borderColor: 'rgba(99, 102, 241, 0.3)',
                  borderRadius: '16px',
                  height: '32px',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                  '& .MuiChip-deleteIcon': {
                    color: '#9CA3AF',
                    fontSize: '1rem',
                    '&:hover': {
                      color: '#F9FAFB',
                    }
                  }
                }}
              />
            ))}

            <StyledInputBase
              multiline
              maxRows={5}
              placeholder={
                disabled 
                  ? "Please upload a document first..." 
                  : selectedDocs.length > 0 
                    ? (selectedDocs.length === 1 
                        ? `Search specifically in "${selectedDocs[0].file_name}"...` 
                        : `Search specifically in ${selectedDocs.length} selected documents...`)
                    : "Message RAG AI (type @ for documents)..."
              }
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              disabled={disabled || loading}
            />
          </Box>
          <IconButton 
            color="primary" 
            onClick={handleSend} 
            disabled={!inputValue.trim() || disabled || loading}
            sx={{ 
              p: '8px',
              background: inputValue.trim() && !disabled && !loading ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
              transition: 'all 0.2s',
            }}
          >
            <SendRoundedIcon fontSize="small" />
          </IconButton>
        </InputBox>
      </InputWrapper>
    </ChatContainer>
  );
};

export default ChatInterface;
