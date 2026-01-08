# LangOrch
**Multi-Tenant RAG Platform with Async Operations**

🚀 Production-ready, multi-tenant RAG orchestration platform with background task processing

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/next.js-14%2B-black.svg)](https://nextjs.org/)
[![Version](https://img.shields.io/badge/version-0.3.0-green.svg)](VERSION)

## 🎯 About LangOrch

LangOrch is a **multi-tenant SaaS platform** for **Retrieval-Augmented Generation (RAG)** with enterprise-grade features:

- ✅ **Production-Ready v0.3.0**: Async operations, smart caching, timeout-free processing
- 🏢 **Multi-Tenant Architecture**: Complete data isolation per tenant
- 🤖 **Multi-Provider LLM**: OpenAI, Anthropic, Ollama support via LiteLLM
- 📊 **Vector Search**: Qdrant integration for semantic document search
- 🔐 **Enterprise Security**: HashiCorp Vault, JWT auth, tenant isolation
- ⚡ **Background Processing**: No timeouts on long-running operations (10+ minutes)

## ✨ Current Features (v0.3.0)

### Document RAG Operations
- **Summarize**: Generate concise document summaries with smart caching
- **Ask**: Question-answering with RAG (vector search + LLM)
- **Transform**: Document transformation (translate, format, extract, etc.)

### Core Capabilities
- **Async Background Tasks**: All LLM operations run in background with polling
- **Smart Summary Caching**: Reuse existing summaries, optional force regeneration
- **Multi-Provider Embedding**: OpenAI, Google Gemini, Anthropic Claude, Ollama
- **Dynamic Embedding Dimensions**: Support for different embedding models
- **Tenant Configuration**: Per-tenant LLM and embedding provider settings
- **Document Management**: Upload, process, chunk, and embed PDF/DOCX files

## 🏗️ Tech Stack

### Backend
- **FastAPI** - High-performance async web framework
- **LiteLLM** - Unified LLM API (OpenAI, Anthropic, Ollama)
- **PostgreSQL 16+** - Primary database
- **Qdrant** - Vector database for semantic search
- **Redis 7+** - Caching and session management
- **HashiCorp Vault** - Secure secret management
- **SQLAlchemy** + **Alembic** - ORM and migrations
- **Pydantic** - Data validation
- **structlog** - Structured logging

### Frontend
- **Next.js 14** (App Router)
- **React** with TypeScript
- **shadcn/ui** + **TailwindCSS**
- **Axios** - API client
- **Sonner** - Toast notifications

### Infrastructure
- **Docker** & **Docker Compose**
- **Nginx** (optional reverse proxy)

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- Git

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd langorch

# 2. Create environment file
cp .env.example .env
# Edit .env with your settings

# 3. Start infrastructure services
docker-compose up -d

# 4. Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload

# 5. Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Vault UI**: http://localhost:8200 (Token: dev-root-token)
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## 📚 Version Roadmap

| Version | Status | Description | Release Date |
|---------|--------|-------------|--------------|
| **v0.3.0** | ✅ **Released** | Async RAG operations with smart caching | 2026-01-08 |
| **v0.4.0** | 🚧 In Development | LangGraph multi-agent workflows, streaming | Q1 2026 |
| **v1.0.0** | 📋 Planned | Production-ready, full observability | Q2 2026 |

### v0.3.0 - Current Release

**What's New:**
- Background task processing for all LLM operations (Summarize, Ask, Transform)
- Smart summary caching with force regeneration option
- Extended timeout support (10 minutes) for long operations
- Multi-provider embedding support (OpenAI, Gemini, Claude, Ollama)
- Dynamic embedding dimensions
- Latest summary retrieval endpoint
- Improved error handling and logging

**Bug Fixes:**
- Fixed transform operation timeout issue
- Fixed duplicate LLM operation records
- Improved polling mechanism

[View Full Changelog](CHANGELOG.md)

### v0.4.0 - In Development

**Target Features:**
- LangGraph StateGraph for workflow orchestration
- Real-time chat interface with conversation history
- Server-Sent Events (SSE) streaming responses
- Human-in-the-Loop (HITL) approval system
- PostgresSaver checkpoint persistence
- Workflow templates (RAG, Simple Chat)
- Multi-turn conversation support
- Advanced RAG with document grading

**Development Status:** 📋 Specification complete, ready to start implementation

[View v0.4 Development Guide](docs/development-phases/V0.4_DEVELOPMENT_PROMPT.md) | [View v0.4 Specification](docs/development-phases/V0.4_LANGGRAPH_PROMPT.md)

### v1.0.0 - Production Ready

**Target Features:**
- Complete observability stack (Prometheus, Grafana, LangSmith)
- Kubernetes deployment manifests
- Production-grade monitoring and alerting
- Performance optimizations
- Comprehensive documentation
- Security audit and hardening

## 🏛️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                        │
│                Next.js 14 + shadcn/ui                    │
│         (Document UI, RAG Operations, Settings)          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   BACKEND LAYER                          │
│              FastAPI + Background Tasks                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Tenant Isolation (JWT + Middleware)             │    │
│  │ ├── Auth Service (JWT, Password Hashing)        │    │
│  │ ├── Document Service (Upload, Processing)       │    │
│  │ ├── Embedding Service (Multi-provider)          │    │
│  │ ├── RAG Service (Summarize, Ask, Transform)     │    │
│  │ └── LLM Service (LiteLLM Integration)           │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
        │                 │                   │
        ↓                 ↓                   ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Redis     │  │    Qdrant    │
│  (Main DB)   │  │  (Sessions)  │  │  (Vectors)   │
└──────────────┘  └──────────────┘  └──────────────┘
        │
        ↓
┌──────────────┐
│    Vault     │
│  (Secrets)   │
└──────────────┘
```

## 🔐 Security Features

### Multi-Tenant Isolation
- JWT-based authentication
- Tenant-scoped database queries
- API-level tenant filtering
- Session isolation via Redis

### Secret Management
- HashiCorp Vault for API keys
- Tenant-specific secret storage
- No secrets in code or .env files
- Automatic secret rotation support

### Data Security
- Encrypted connections (TLS/SSL ready)
- Secure password hashing (pwdlib with Argon2)
- Audit logging for critical operations
- GDPR-compliant data handling

## 📖 API Documentation

### RAG Operations

#### Summarize Document
```bash
POST /api/v1/llm/documents/summarize
{
  "document_id": "uuid",
  "model": "llama3.2",  # optional
  "max_length": 500,     # optional
  "force": false         # optional
}
```

#### Ask Question
```bash
POST /api/v1/llm/documents/ask
{
  "document_id": "uuid",
  "question": "What is this document about?",
  "model": "llama3.2",  # optional
  "max_chunks": 5        # optional
}
```

#### Transform Document
```bash
POST /api/v1/llm/documents/transform
{
  "document_id": "uuid",
  "instruction": "Translate to Turkish",
  "model": "llama3.2",        # optional
  "output_format": "text"     # text, markdown, json
}
```

All operations return immediately with an `operation_id`. Use polling to check status:

```bash
GET /api/v1/llm/operations/{operation_id}
```

[Full API Documentation](http://localhost:8000/docs)

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm run test
npm run type-check

# Linting
black backend/app
isort backend/app
flake8 backend/app
```

## 📊 Project Structure

```
langorch/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application
│   │   ├── api/
│   │   │   └── v1/endpoints/          # API endpoints
│   │   ├── core/                      # Config, database, vault
│   │   ├── models/                    # SQLAlchemy models
│   │   ├── schemas/                   # Pydantic schemas
│   │   └── services/                  # Business logic
│   ├── alembic/                       # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── app/                           # Next.js app router
│   ├── components/                    # React components
│   ├── lib/                           # API client, utilities
│   └── package.json
├── docs/                              # Documentation
├── .github/                           # GitHub workflows
├── docker-compose.yml
├── VERSION                            # Current version
├── CHANGELOG.md                       # Version history
└── README.md
```

## 🤝 Contributing

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: add new feature
fix: bug fix
docs: documentation changes
refactor: code refactoring
test: adding or updating tests
chore: maintenance tasks
```

### Git Workflow

See [Branching Strategy](.github/BRANCHING_STRATEGY.md) for details.

```bash
# Create feature branch
git checkout develop/v0.4
git checkout -b feature/my-feature

# Commit changes
git add .
git commit -m "feat: add amazing feature"

# Push and create PR
git push origin feature/my-feature
```

## 📝 License

[License information to be added]

## 👥 Contact

[Contact information to be added]

## 🙏 Acknowledgments

Built with these amazing open-source projects:

- [FastAPI](https://fastapi.tiangolo.com/)
- [LiteLLM](https://github.com/BerriAI/litellm)
- [Qdrant](https://qdrant.tech/)
- [Next.js](https://nextjs.org/)
- [shadcn/ui](https://ui.shadcn.com/)
- [HashiCorp Vault](https://www.vaultproject.io/)

---

**Current Status**: v0.3.0 - Production ready for basic RAG operations

**Next Up**: v0.4.0 - LangGraph integration and streaming responses

For detailed development information, see [Development Phases](docs/development-phases/)
