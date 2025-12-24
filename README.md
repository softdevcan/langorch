# LangOrch
**Language Workflow Orchestration Platform**

🚀 Graph-as-a-Service mimarisi ile modern SaaS RAG orkestrasyon platformu

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/next.js-14%2B-black.svg)](https://nextjs.org/)

## 🎯 Proje Hakkında

LangOrch, **Graph-as-a-Service** mimarisi üzerine kurulu, **çok kiracılı (multi-tenant)**, **hibrit LLM destekli** ve **Human-in-the-Loop** yetenekleri ile donatılmış modern bir SaaS RAG orkestrasyon platformudur.

### Temel Özellikler

- 🔗 **Graph-as-a-Service**: LangGraph ile dinamik workflow yönetimi
- 🏢 **Multi-Tenant İzolasyon**: Enterprise seviye tenant güvenliği (RLS + Application layer)
- 🤖 **Hibrit LLM**: OpenAI, Anthropic, Ollama ve daha fazlası (LiteLLM)
- 👤 **Human-in-the-Loop**: Kritik noktalarda insan onay mekanizmaları
- 📊 **Vector Search**: pgvector + Qdrant ile semantic search
- 🔐 **Secret Management**: HashiCorp Vault entegrasyonu
- ⚡ **Real-time Streaming**: SSE ile canlı token streaming
- 📈 **Scalable**: Milyonlarca kullanıcı için tasarlanmış mimari

## 🏗️ Teknoloji Yığını

### Backend
- **FastAPI** (Python 3.11+) - Async web framework
- **LangGraph** - Agent orkestrasyon motoru
- **LiteLLM** - Unified LLM API & cost optimization
- **PostgreSQL 16+** + **pgvector** - İlişkisel veritabanı & vektör arama
- **Redis 7+** - Cache & session yönetimi
- **Qdrant** - Vektör veritabanı
- **HashiCorp Vault** - Secret management
- **SQLAlchemy** + **Alembic** - ORM & migrations
- **Pydantic** - Data validation
- **structlog** - Structured logging

### Frontend
- **Next.js 14+** (App Router) - React framework
- **React Flow** - Workflow görselleştirme
- **Zustand** - State management
- **shadcn/ui** + **TailwindCSS** - UI component library
- **React Query** - Server state management
- **Axios** - HTTP client

### Infrastructure
- **Docker** & **Docker Compose** - Containerization
- **Nginx** - Reverse proxy & load balancing
- **Prometheus** & **Grafana** - Monitoring
- **GitHub Actions** - CI/CD

## 🚀 Hızlı Başlangıç

### Gereksinimler

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- Git

### Kurulum

```bash
# 1. Repository'yi klonla
git clone <repository-url>
cd langorch

# 2. Environment dosyasını oluştur
cp .env.example .env

# 3. Docker servisleri başlat (PostgreSQL, Redis, Vault, Qdrant)
docker-compose up -d

# 4. Backend kurulumu
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Database migrations
alembic upgrade head

# Backend'i başlat
uvicorn app.main:app --reload

# 5. Frontend kurulumu (yeni terminal)
cd frontend
npm install
npm run dev
```

### Erişim

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Vault UI**: http://localhost:8200 (Token: dev-root-token)

## 📚 Geliştirme Süreci

Bu proje **paralel ve dengeli geliştirme** prensibiyle tasarlanmıştır.

### 📖 Doküman Rehberi

Hangi durumda hangi dokümanı okumalısınız?

| Durum | Doküman | Açıklama |
|-------|---------|----------|
| 🆕 **İlk kez başlıyorum** | [Getting Started](docs/GETTING_STARTED.md) | 5 dakikada setup, öğrenme yolu, ilk katkı |
| 🏗️ **Stratejiyi anlamak istiyorum** | [Parallel Development](docs/PARALLEL_DEVELOPMENT.md) | Neden paralel? Nasıl çalışır? Best practices |
| 📋 **Versiyonları görmek istiyorum** | [Development Phases](docs/development-phases/README.md) | v0.1, v0.2, v0.3, v1.0 hedefleri ve görevleri |
| ✅ **İlerlemeyi takip edeceğim** | [Development Roadmap](docs/DEVELOPMENT_ROADMAP.md) | Detaylı checklist, sprint planning, notlar |
| ⚡ **Hızlı komutlar lazım** | [Version Quick Start](docs/VERSION_QUICKSTART.md) | Her versiyon için komutlar, troubleshooting |

👉 **Başlamak için**: [Getting Started](docs/GETTING_STARTED.md)

### Versiyon Roadmap

| Version | Hedef | Durum | Doküman |
|---------|-------|-------|---------|
| **v0.1** | MVP - Authentication & Basic CRUD | 🏗️ In Progress | [Version 0.1](docs/development-phases/README.md#-version-01-mvp---authentication--basic-crud) |
| **v0.2** | Security & Document Management | 📋 Planned | [Version 0.2](docs/development-phases/README.md#-version-02-security--document-management) |
| **v0.3** | LangGraph & Chat Interface | 📋 Planned | [Version 0.3](docs/development-phases/README.md#-version-03-langgraph--chat-interface) |
| **v1.0** | Production Ready | 📋 Planned | [Version 1.0](docs/development-phases/README.md#-version-10-production-ready) |

### Geliştirme Fazları

Detaylı teknik dokümanlar:

- [📄 Faz 0: Altyapı Kurulumu](docs/development-phases/faz-0-kurulum.md)
- [📄 Faz 1: Backend Temel Yapı](docs/development-phases/faz-1-backend.md)
- [📄 Faz 2: Veritabanı & Güvenlik](docs/development-phases/faz-2-database-security.md)
- [📄 Faz 3: LangGraph Orkestrasyon](docs/development-phases/faz-3-langgraph.md)
- [📄 Faz 4: Frontend Geliştirme](docs/development-phases/faz-4-frontend.md)
- [📄 Faz 5: Production Deployment](docs/development-phases/faz-5-deployment.md)

## 🏛️ Mimari Genel Bakış

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                        │
│              Next.js + React Flow                        │
│         (Chat UI, Workflow Editor, Dashboard)            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    API GATEWAY                           │
│                   Nginx + SSL/TLS                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   BACKEND LAYER                          │
│    FastAPI + LangGraph + LiteLLM                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Tenant Isolation (JWT + RLS + Middleware)       │    │
│  │ ├── Auth Service                                │    │
│  │ ├── Document Service (Embedding, Chunking)      │    │
│  │ ├── Workflow Service (LangGraph)                │    │
│  │ └── Vector Search (pgvector + Qdrant)          │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
        │                 │                   │
        ↓                 ↓                   ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Redis     │  │    Qdrant    │
│  + pgvector  │  │  (Sessions)  │  │   (Vectors)  │
│  + RLS       │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
        │
        ↓
┌──────────────┐
│    Vault     │
│  (Secrets)   │
└──────────────┘
```

## 🔐 Güvenlik Özellikleri

### Multi-Layer Tenant Isolation

1. **Database Layer**: PostgreSQL Row Level Security (RLS)
2. **Application Layer**: Explicit tenant filtering in queries
3. **Middleware Layer**: Tenant context injection
4. **API Layer**: JWT-based authentication & authorization

### Secret Management

- HashiCorp Vault ile güvenli secret storage
- Tenant-specific API key isolation
- Automatic secret rotation support
- No secrets in code or environment variables

### Data Security

- Encryption at rest (PostgreSQL)
- Encryption in transit (TLS/SSL)
- Audit logging tüm kritik operasyonlar için
- GDPR-compliant data retention policies

## 🧪 Test ve Kalite

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm run test
npm run type-check

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 📊 Monitoring & Logging

- **Structured Logging**: structlog ile JSON formatted logs
- **Metrics**: Prometheus ile custom metrics
- **Visualization**: Grafana dashboards
- **Tracing**: Request tracing (gelecek)
- **Alerting**: Alert rules for critical events

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'feat: add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

### Commit Conventions

Conventional Commits kullanıyoruz:

```
feat: yeni özellik
fix: bug düzeltme
docs: dokümantasyon değişikliği
style: kod formatı (logic değişikliği yok)
refactor: kod refactoring
test: test ekleme/düzeltme
chore: build process, dependency updates
```

## 📖 Proje Yapısı

```
langorch/
├── backend/                       # Backend kaynak kodları
│   ├── app/
│   │   ├── main.py               # FastAPI application
│   │   ├── core/                 # Core modules (config, database, security)
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── api/                  # API endpoints
│   │   ├── services/             # Business logic
│   │   ├── workflows/            # LangGraph workflows
│   │   └── middleware/           # Middleware (tenant, logging, etc.)
│   ├── alembic/                  # Database migrations
│   ├── tests/                    # Backend tests
│   └── requirements.txt          # Python dependencies
│
├── frontend/                      # Frontend kaynak kodları
│   ├── src/
│   │   ├── app/                  # Next.js app directory
│   │   ├── components/           # React components
│   │   ├── lib/                  # Utilities & API client
│   │   └── stores/               # Zustand stores
│   ├── public/                   # Static assets
│   └── package.json              # Node dependencies
│
├── docs/                          # Dokümantasyon
│   ├── development-phases/       # Faz dokümantasyonları
│   ├── architecture/             # Mimari dokümanlar
│   └── api/                      # API dokümantasyonu
│
├── infrastructure/                # Infrastructure as Code
│   ├── docker/                   # Dockerfiles
│   ├── k8s/                      # Kubernetes manifests
│   └── terraform/                # Terraform configs
│
├── docker-compose.yml            # Development environment
├── .env.example                  # Environment variables template
└── README.md                     # Bu dosya
```

## 🌟 Use Cases

### 1. Customer Support RAG System
- Multi-tenant document management
- Semantic search ile knowledge base
- Human-in-loop approvals
- Custom workflows per tenant

### 2. Enterprise Document Intelligence
- Secure document upload & processing
- Advanced embeddings & chunking
- Cross-document semantic search
- Tenant-isolated data

### 3. AI Agent Orchestration
- LangGraph ile complex workflows
- Multi-step reasoning
- Tool integration
- Real-time streaming responses

## 📝 Lisans

[Lisans bilgisi eklenecek]

## 👥 İletişim

[İletişim bilgileri eklenecek]

## 🙏 Teşekkürler

Bu proje aşağıdaki açık kaynak projeleri kullanır:

- [FastAPI](https://fastapi.tiangolo.com/)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [Next.js](https://nextjs.org/)
- [React Flow](https://reactflow.dev/)
- [shadcn/ui](https://ui.shadcn.com/)

---

**Not**: Bu proje aktif geliştirme aşamasındadır. Production kullanımı için [Version 1.0](docs/development-phases/README.md#-version-10-production-ready) beklenmesi önerilir.

**Geliştirmeye başlamak için**: [Geliştirme Dokümanları](docs/development-phases/README.md)
