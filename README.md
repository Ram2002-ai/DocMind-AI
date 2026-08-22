# DocuMind AI

DocuMind AI is a full-stack document intelligence platform for uploading, processing, and querying documents with retrieval-augmented generation (RAG). It combines a FastAPI backend for extraction, embedding, and LLM orchestration with a React workspace for multi-thread chat, file attachments, and streamed responses.

## Overview

DocuMind AI ingests PDFs, images, and plain-text files, extracts and normalizes their content, chunks and embeds the text, and stores vectors in ChromaDB for semantic retrieval. Users can ask questions in a chat interface and receive answers grounded in uploaded documents, with support for streaming responses and source attribution.

The platform is designed for modular development: backend services are separated by concern, and the frontend communicates through a stable API contract that can run against a built-in mock backend during UI development.

## Capabilities

### Document processing

- PDF text extraction with PyMuPDF and OCR fallback for scanned pages
- Image OCR via EasyOCR with preprocessing
- Text normalization and configurable chunking with metadata
- Semantic embeddings using Sentence Transformers
- Vector storage and retrieval in ChromaDB

### AI and RAG

- Semantic search across document collections
- RAG-powered chat with streamed LLM responses via OpenRouter
- Document summarization and entity extraction (emails, phone numbers, dates)
- Multi-document analysis within a conversation thread

### Workspace UI

- Multi-thread chat with sidebar navigation
- Drag-and-drop upload for PDF, image, and text files
- Real-time streaming responses with automatic non-streaming fallback
- Attachment management per thread
- Mock API mode for frontend-only development

### Platform

- FastAPI REST API with OpenAPI documentation
- PostgreSQL for relational metadata
- JWT-based authentication (available in extended API routes)
- Per-user data isolation
- Docker Compose support for core infrastructure services

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              React + Vite Frontend (documind-frontend)       │
│                    TypeScript, SSE streaming                 │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP / Server-Sent Events
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                         │
│         Routes · Services · Models · Repositories            │
└──────────┬─────────────────┬─────────────────┬──────────────┘
           │                 │                 │
      ┌────▼────┐      ┌─────▼─────┐    ┌─────▼─────┐
      │PostgreSQL│      │ ChromaDB  │    │ OpenRouter │
      │ (metadata)│     │ (vectors) │    │   (LLM)    │
      └─────────┘      └───────────┘    └────────────┘
```

### Processing pipeline

```
Upload → Validation → Extraction → Text cleaning → Chunking
  → Embedding → ChromaDB → PostgreSQL metadata → Ready for chat/search
```

## Tech stack

| Layer | Technologies |
| --- | --- |
| Backend | FastAPI, SQLAlchemy, Pydantic, Alembic |
| Document AI | PyMuPDF, EasyOCR, Sentence Transformers, ChromaDB |
| LLM | OpenRouter (configurable model) |
| Frontend | React 19, TypeScript, Vite, React Router |
| Data | PostgreSQL, ChromaDB |
| Infrastructure | Docker, Docker Compose |

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 14+ (or use Docker Compose)
- [OpenRouter](https://openrouter.ai/) API key
- Docker and Docker Compose (optional, recommended for databases)

## Getting started

### 1. Clone the repository

```bash
git clone <repository-url>
cd DocuMind-AI-main
```

### 2. Configure the backend

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set at minimum:

| Variable | Description |
| --- | --- |
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `JWT_SECRET` | A secure random string for token signing |
| `DATABASE_URL` | PostgreSQL connection string |

Other settings such as embedding model, chunk size, and CORS origins are documented in `backend/.env.example`.

### 3. Configure the frontend

```bash
cd documind-frontend
cp .env.example .env
npm install
```

For frontend-only development, leave `VITE_USE_MOCK_API=true` in `.env`. The UI runs entirely against an in-memory mock backend with no server required.

To connect to the live backend:

```env
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=http://localhost:8000
```

### 4. Run with Docker Compose (databases and backend)

Start PostgreSQL, ChromaDB, and the FastAPI backend:

```bash
docker-compose up -d postgres chromadb backend
```

| Service | URL |
| --- | --- |
| Backend API | http://localhost:8000 |
| API documentation | http://localhost:8000/docs |
| ChromaDB | http://localhost:8001 |

Run the frontend locally:

```bash
cd documind-frontend
npm run dev
```

The Vite dev server typically runs at http://localhost:5173.

### 5. Run locally without Docker

**Backend**

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Ensure PostgreSQL and ChromaDB are running and that `backend/.env` points to them.

**Frontend**

```bash
cd documind-frontend
npm install
npm run dev
```

## API reference

### Active workspace endpoints

The frontend integrates with the workspace chat API under `/api/threads`:

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/threads` | List conversation threads |
| `POST` | `/api/threads` | Create a new thread |
| `DELETE` | `/api/threads/{id}` | Delete a thread |
| `GET` | `/api/threads/{id}/messages` | Retrieve message history |
| `POST` | `/api/threads/{id}/files` | Upload a file (multipart) |
| `DELETE` | `/api/threads/{id}/files/{fileId}` | Remove an attachment |
| `POST` | `/api/threads/{id}/chat/stream` | Stream a chat response (SSE) |

Interactive documentation is available at http://localhost:8000/docs when the backend is running.

### Extended API routes

Additional route modules exist under `backend/app/api/routes/` for authentication, documents, search, summaries, and entities under the `/api/v1` prefix. These can be registered in `backend/app/main.py` for the full production API surface.

For frontend integration details, see [documind-frontend/README.md](documind-frontend/README.md).

## Project structure

```
DocuMind-AI-main/
├── backend/
│   ├── app/
│   │   ├── main.py              # Application entry point
│   │   ├── api/routes/          # REST endpoints
│   │   ├── core/                # Configuration, security, logging
│   │   ├── db/                  # Database session and base models
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # Business and AI/ML logic
│   │   ├── repositories/        # Data access layer
│   │   └── utils/               # Shared utilities
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── documind-frontend/
│   ├── src/
│   │   ├── api/                 # HTTP client, SSE parser, mock backend
│   │   ├── components/          # UI components
│   │   ├── hooks/               # React hooks for threads, chat, upload
│   │   └── types.ts             # Shared TypeScript types
│   ├── package.json
│   └── .env.example
├── docker-compose.yml
├── IMPLEMENTATION_GUIDE.md
└── README.md
```

## Development

### Backend

```bash
cd backend
pytest                  # Run tests
black app/              # Format code
flake8 app/             # Lint
mypy app/               # Type checking
```

### Frontend

```bash
cd documind-frontend
npm run dev             # Development server
npm run build           # Production build
npm run preview         # Preview production build
npm run lint            # Lint with oxlint
```

## Security

- JWT authentication with bcrypt password hashing
- User-scoped document and conversation isolation
- File type and size validation on upload
- Configurable CORS origins
- Secrets managed through environment variables
- Parameterized database queries via SQLAlchemy

## Documentation

- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) — Development roadmap and implementation notes
- [documind-frontend/README.md](documind-frontend/README.md) — Frontend architecture and API contract
- [Backend OpenAPI docs](http://localhost:8000/docs) — Interactive API reference (when running locally)

## Contributing

Contributions are welcome. When proposing changes, keep diffs focused, follow existing conventions in each module, and update relevant documentation when behavior or configuration changes.

---

**DocuMind AI** — Intelligent document processing and conversational search powered by modern AI infrastructure.
