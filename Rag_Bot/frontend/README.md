# RAG Chatbot Frontend - README

A modern, modular React + Material-UI chatbot interface for the RAG (Retrieval Augmented Generation) pipeline.

## 🚀 Features

- **Modern UI**: Built with Material-UI for a professional look
- **Drag & Drop Upload**: Easy PDF document uploads
- **Interactive Chat**: Real-time question answering
- **Source Attribution**: View retrieved documents with scores
- **Retrieval Options**: Configure search parameters (dense/hybrid, top-k, etc.)
- **Document Management**: Upload, list, and delete documents
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Real-time Feedback**: Loading states, error handling, progress indicators

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatInterface.js          # Main chat window
│   │   ├── MessageBubble.js          # Individual message display
│   │   ├── DocumentUpload.js         # PDF upload component
│   │   ├── DocumentList.js           # Document gallery
│   │   └── RetrievalOptions.js       # Query configuration
│   ├── services/
│   │   └── ApiService.js             # Backend API integration
│   ├── utils/
│   │   └── helpers.js                # Utility functions
│   ├── App.js                        # Main app component
│   ├── index.js                      # Entry point
│   └── .env.example                  # Environment template
├── public/
│   └── index.html                    # HTML template
├── webpack.config.js                 # Webpack configuration
├── .babelrc                          # Babel configuration
└── package.json                      # Dependencies

Components/Modules:
- **ChatInterface**: Manages chat window, message display, and input
- **MessageBubble**: Renders individual messages (user/assistant)
- **DocumentUpload**: Handles PDF uploads with drag-and-drop
- **DocumentList**: Displays uploaded documents in card format
- **RetrievalOptions**: Configure retrieval parameters
- **ApiService**: Centralized API communication
- **Helpers**: Utilities for formatting and data processing
```

## 🛠️ Installation

### Prerequisites

- Node.js 14+ 
- npm or yarn

### Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Or with yarn
yarn install
```

## 🚀 Running the Application

### Development Server

```bash
# Start with hot reload
npm start

# Or with yarn
yarn start

# Server runs on http://localhost:3000
```

### Production Build

```bash
# Build for production
npm run build

# Serves files in dist/ directory
```

### Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your backend URL
REACT_APP_API_URL=http://localhost:8000
```

## 📊 Architecture

### Component Hierarchy

```
App (Main Container)
├── ChatInterface
│   ├── MessagesContainer
│   │   └── MessageBubble (repeated)
│   └── InputArea
├── DocumentUpload
├── DocumentList
│   └── DocumentCard (repeated)
└── RetrievalOptions
    ├── Mode Selector
    ├── Top-K Slider
    ├── Document Filter
    └── Metadata Toggle
```

### Data Flow

```
User Input (Chat/Upload)
    ↓
App Component (State Management)
    ↓
ApiService (Backend Communication)
    ↓
Component Re-render
    ↓
Updated UI
```

## 🔌 API Integration

### Backend Endpoints Used

All endpoints are defined in `ApiService.js`:

- `GET /health` - System status
- `GET /ping` - Health check
- `POST /documents/upload` - Upload PDF
- `GET /documents/` - List documents
- `DELETE /documents/{id}` - Delete document
- `POST /query/hybrid` - Hybrid search
- `POST /query/dense` - Dense search
- `POST /query/ask` - Auto query

### Error Handling

- Centralized error handling in ApiService
- User-friendly error messages
- Retry suggestions
- API health monitoring

## 🎨 Styling

Built with Material-UI components:
- **Responsive Grid Layout** - Adapts to screen size
- **Material Design** - Professional appearance
- **Dark Mode Ready** - Theme configuration in App.js
- **Custom Colors** - Primary blue (#2196F3), secondary red (#F50057)
- **Smooth Animations** - Transitions and hover effects

## 🔑 Key Features Explained

### Chat Interface
- Auto-scrolling message list
- User (right) vs Assistant (left) messages
- Expandable source citations
- Real-time typing indicator
- Clear chat history

### Document Upload
- Drag-and-drop support
- File validation (PDF only, max 50MB)
- Progress indication
- Success/error feedback

### Retrieval Options
- **Mode Selection**: Dense (semantic) or Hybrid (semantic + keyword)
- **Top-K**: Adjust number of results (1-20)
- **Document Filter**: Search specific or all documents
- **Metadata Toggle**: Show/hide source information

### Message Display
- Formatted text with line breaks
- Processing time indicator
- Expandable source chunks
- Score/confidence indicators
- Error messages with details

## 📱 Responsive Breakpoints

- **Mobile** (< 600px): Single column, full-width
- **Tablet** (600-960px): Single column, constrained width
- **Desktop** (960px+): Two-column layout (chat + sidebar)

## 🔐 Security

- Environment variables for sensitive data
- No API keys in code
- Secure file upload validation
- CORS-enabled for backend communication
- Input sanitization for user queries

## 🚀 Performance

- Code splitting for faster initial load
- Asset optimization in production
- Lazy loading of components (future)
- Efficient re-renders with React hooks
- Optimized bundle size

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Use different port
npm start -- --port 3001
```

### API Connection Failed

Check .env file:
```bash
REACT_APP_API_URL=http://localhost:8000
```

### Build Issues

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Hot Reload Not Working

```bash
# Restart dev server
npm start
```

## 🔄 Development Workflow

1. **Create Component**: New file in `src/components/`
2. **Add Styling**: Use Material-UI `styled()` API
3. **Integrate API**: Add methods to `ApiService.js`
4. **Update State**: Manage in App.js with hooks
5. **Test**: Hot reload during development

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| React | UI Framework |
| ReactDOM | DOM Rendering |
| Material-UI | Component Library |
| @emotion | Styling Engine |
| Axios | HTTP Client |
| Webpack | Bundler |
| Babel | JS Transpiler |

## 🌟 Future Enhancements

- [ ] Dark mode toggle
- [ ] Export chat history
- [ ] Message bookmarking
- [ ] Advanced search filters
- [ ] File upload preview
- [ ] Real-time collaboration
- [ ] Voice input
- [ ] Multi-language support

## 📚 Resources

- [React Documentation](https://react.dev)
- [Material-UI Documentation](https://mui.com)
- [Webpack Documentation](https://webpack.js.org)
- [Axios Documentation](https://axios-http.com)

## 🤝 Contributing

Feel free to extend and customize the components for your needs!

## 📝 License

MIT License

---

**Questions?** Check the parent project README for backend setup instructions!
