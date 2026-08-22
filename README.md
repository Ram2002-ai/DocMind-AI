# DocuMind AI - Production-Grade Document Intelligence Platform

A full-stack AI application for intelligent document processing, extraction, and analysis using modern web technologies and advanced AI/ML capabilities.

## 🎯 Features

### Document Processing
- ✅ **PDF Text Extraction** - PyMuPDF with OCR fallback for scanned PDFs
- ✅ **Image OCR** - EasyOCR with image preprocessing
- ✅ **Text Cleaning** - Intelligent text normalization
- ✅ **Automatic Chunking** - Configurable text segmentation with metadata
- ✅ **Embeddings** - Sentence Transformers for semantic search
- ✅ **Vector Database** - ChromaDB with metadata filtering

### AI & RAG
- ✅ **Semantic Search** - Find relevant information across documents
- ✅ **RAG Chat** - Ask questions about documents with source attribution
- ✅ **AI Summaries** - Automatic document summarization via OpenRouter LLMs
- ✅ **Entity Extraction** - Extract emails, phone numbers, dates
- ✅ **Multi-Document Analysis** - Search and chat across multiple documents

### User Experience
- ✅ **Professional Dashboard** - Document management and statistics
- ✅ **Real-time Processing** - Visual upload and processing pipeline
- ✅ **Document Library** - Searchable document management
- ✅ **Document Viewer** - Extracted text and metadata display
- ✅ **Chat Interface** - ChatGPT-style document Q&A
- ✅ **Responsive Design** - Mobile-friendly interface

### Architecture
- ✅ **FastAPI Backend** - Modern, type-safe REST API
- ✅ **React Frontend** - With TypeScript and Tailwind CSS
- ✅ **PostgreSQL** - Relational database for metadata
- ✅ **JWT Authentication** - Secure user authentication
- ✅ **User Isolation** - Complete data privacy per user
- ✅ **Clean Architecture** - Modular, testable, maintainable code

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React + Vite Frontend                    │
│              (TypeScript, Tailwind, TanStack Query)          │
└──────────────────────┬──────────────────────────────────────┘
                       │ (Axios, JWT Auth)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│        (Services, Routes, Models, Repositories)             │
└──────────┬────────────┬────────────┬────────────────────────┘
           │            │            │
      ┌────▼──┐  ┌──────▼──┐  ┌─────▼─────┐
      │   DB  │  │ ChromaDB │  │ OpenRouter│
      │ (PG)  │  │ (Vectors)│  │   (LLM)   │
      └───────┘  └──────────┘  └───────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 14+
- OpenRouter API Key
- Docker & Docker Compose (optional)

### Environment Setup

```bash
# Clone/setup repository
cd documind-ai

# Copy environment template
cp backend/.env.example backend/.env

# Update backend/.env with your credentials
# - OPENROUTER_API_KEY: Your OpenRouter API key
# - OPENROUTER_MODEL: Default model slug, e.g. openai/gpt-5-mini
# - JWT_SECRET: Generate a secure random key
# - DATABASE_URL: PostgreSQL connection string
```

### Option 1: Docker Compose (Recommended for Development)

```bash
# Start all services
docker-compose up -d

# Services will be available at:
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Backend Docs: http://localhost:8000/docs
# ChromaDB: http://localhost:8001
```

### Option 2: Local Setup

**Backend:**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
python -m uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## 📁 Project Structure

```
documind-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI application
│   │   ├── core/                   # Config, security, logging
│   │   ├── api/routes/             # API endpoints
│   │   ├── models/                 # SQLAlchemy models
│   │   ├── schemas/                # Pydantic schemas
│   │   ├── services/               # Business logic
│   │   ├── repositories/           # Data access
│   │   ├── db/                     # Database config
│   │   └── utils/                  # Utilities
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── api/                    # API clients
│   │   ├── components/             # React components (to build)
│   │   ├── pages/                  # Page components (to build)
│   │   ├── hooks/                  # Custom React hooks
│   │   ├── types/                  # TypeScript types
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
│
├── docker-compose.yml
├── setup.sh
└── README.md
```

## 🔑 Key API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/me` - Get current user

### Documents
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents` - List documents
- `GET /api/v1/documents/{id}` - Get document details
- `GET /api/v1/documents/{id}/text` - Get extracted text
- `DELETE /api/v1/documents/{id}` - Delete document

### Chat & RAG
- `POST /api/v1/chat` - Send chat message
- `GET /api/v1/chat/conversations` - List conversations
- `GET /api/v1/chat/conversations/{id}` - Get conversation messages

### AI Features
- `POST /api/v1/search` - Semantic search
- `POST /api/v1/documents/{id}/summary` - Generate summary
- `POST /api/v1/documents/{id}/entities` - Extract entities

Full API documentation: `http://localhost:8000/docs`

## 🔒 Security Features

- ✅ **JWT Authentication** - Stateless user authentication
- ✅ **Password Hashing** - bcrypt password security
- ✅ **User Isolation** - Data privacy per user
- ✅ **File Validation** - Type and size restrictions
- ✅ **CORS Configuration** - Cross-origin request control
- ✅ **Environment Variables** - No secrets in code
- ✅ **SQL Injection Prevention** - SQLAlchemy parameterized queries
- ✅ **Path Traversal Protection** - Safe file handling

## 📊 Data Flow

```
Upload PDF/Image
    ↓
[FastAPI Upload Endpoint]
    ↓
[File Validation & Storage]
    ↓
[Background Processing] → [Extraction Service]
    ↓
[Text Cleaning Service]
    ↓
[Chunking Strategy]
    ↓
[Embedding Service] (Sentence Transformers)
    ↓
[Vector Database] (ChromaDB)
    ↓
[PostgreSQL Metadata]
    ↓
Document Ready for:
  • Chat (RAG)
  • Search (Semantic)
  • Summary (OpenRouter)
  • Entities (Regex)
```

## 🛠️ Development

### Backend Development

```bash
cd backend

# Run tests
pytest

# Format code
black app/

# Lint
flake8 app/

# Type checking
mypy app/
```

### Frontend Development

```bash
cd frontend

# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint
npm run lint
```

## 📋 TODO - Next Development Tasks

### Frontend Components (Priority)
- [ ] UI component library (Button, Input, Modal, Card, etc.)
- [ ] Layout components (Header, Sidebar, PageContainer)
- [ ] Document components (DocumentCard, DocumentTable, UploadDropzone)
- [ ] AI components (ChatMessage, SourceCitation, TypingIndicator)

### Frontend Pages
- [ ] LoginPage with email/password form
- [ ] DashboardPage with stats and recent documents
- [ ] UploadPage with drag-and-drop
- [ ] DocumentLibraryPage with filtering/sorting
- [ ] DocumentViewerPage with 3-column layout
- [ ] ChatPage with RAG interface
- [ ] SearchPage for semantic search
- [ ] EntitiesPage for extracted entities

### Quality Improvements
- [ ] Backend tests (pytest)
- [ ] Frontend tests (vitest)
- [ ] Error handling & validation
- [ ] Loading states & skeleton loaders
- [ ] Empty states
- [ ] Error boundaries
- [ ] Logging & monitoring

### Deployment
- [ ] Database migrations (Alembic)
- [ ] Environment configuration
- [ ] Production Dockerfile optimization
- [ ] Kubernetes manifests (optional)
- [ ] CI/CD pipeline (GitHub Actions)

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/

# Frontend tests
cd frontend
npm run test
```

## 📚 Technologies Used

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation
- **PyMuPDF** - PDF text extraction
- **EasyOCR** - Image OCR
- **Sentence Transformers** - Text embeddings
- **ChromaDB** - Vector database
- **OpenRouter** - LLM routing and model access

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Router** - Navigation
- **TanStack Query** - Server state management
- **Axios** - HTTP client
- **Zustand** - Client state management

### Infrastructure
- **PostgreSQL** - Relational database
- **ChromaDB** - Vector database
- **Docker** - Containerization
- **Docker Compose** - Local development

## 📖 Documentation

- [Backend API Docs](/backend/API.md) - Detailed API documentation
- [Frontend Guide](/frontend/GUIDE.md) - Frontend development guide
- [Deployment Guide](/docs/DEPLOYMENT.md) - Production deployment
- [Architecture Details](/docs/ARCHITECTURE.md) - System architecture

## 🤝 Contributing

This is a demonstration of production-grade fullstack AI application architecture. For improvements or questions, please refer to the detailed session progress notes.

## 📄 License

MIT License - See LICENSE file

## 🎓 Learning Resource

This codebase demonstrates:
- Production-grade FastAPI architecture
- Modern React development patterns
- RAG (Retrieval-Augmented Generation) implementation
- Vector database integration
- JWT authentication
- Modular service-based architecture
- Clean code practices

## 📞 Support

For issues or questions:
1. Check the [API documentation](/docs) at http://localhost:8000/docs
2. Review service implementations in `backend/app/services/`
3. Check component implementations in `frontend/src/components/`

---

**Status**: Feature-complete backend, Frontend foundation ready for component development

**Next Steps**: Build React UI components and pages using the provided hooks and API clients.
#   D o c M i n d - A I  
 