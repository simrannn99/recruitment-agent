# 🤖 AI-Powered Recruitment Platform

**Intelligent resume screening with semantic vector search, LLM analysis, real-time WebSocket updates, and asynchronous processing**

A production-ready recruitment platform combining **Sentence Transformers** for semantic matching, **LLM-powered resume analysis** (Ollama/OpenAI), **pgvector** for efficient similarity search, and **Django Channels** for real-time updates at scale.

---

## ✨ AI/ML Features

### 🧠 **Semantic Vector Search**
- **Sentence Transformers** (`all-MiniLM-L6-v2`) for 384-dimensional embeddings
- **pgvector** extension for cosine similarity search in PostgreSQL
- **Automatic embedding generation** via Django signals on content updates
- **Sub-100ms search** on 10K+ candidates with IVFFlat indexing

### 🤖 **LLM-Powered Analysis**
- **Flexible LLM backend**: Switch between Ollama (local, free) or OpenAI (cloud, paid)
- **Structured output**: Match scores (0-100), skill gap analysis, interview questions
- **Async processing**: Non-blocking analysis via Celery task queues
- **Retry logic**: Exponential backoff for robust LLM interactions

### 🎯 **Intelligent Matching**
- **Candidate-Job matching**: Find top candidates for any job posting
- **Job-Candidate matching**: Discover best job opportunities for candidates
- **Similar candidate search**: Build talent pools with semantic similarity
- **Collapsible admin UI**: Clean, expandable dropdowns for matching results

### 🔌 **WebSocket Real-Time Updates**
- **Django Channels** for WebSocket support with Daphne ASGI server
- **Real-time task notifications** for background job completion (embeddings, AI analysis)
- **Auto-refresh admin interface** when analysis completes
- **Redis channel layer** for message broadcasting across workers
- **Automatic reconnection** with exponential backoff
- **WebSocket test page** at `/ws-test/` for monitoring task progress

### ⚡ **Event-Driven Architecture**
- **Django signals**: Auto-trigger embedding generation on model save
- **Priority-based queues**: High (emails), Embeddings, Medium (LLM), Low (cleanup)
- **Real-time monitoring**: Flower dashboard for task tracking
- **Horizontal scaling**: Distributed Celery workers

---

## 🚀 Quick Start

See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for detailed technical documentation.

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose**
- **Ollama** (for local LLM) OR **OpenAI API key** (for cloud LLM)

### Installation

```bash
# Clone repository
git clone https://github.com/simrannn99/recruitment-agent.git
cd recruitment-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Deployment Options

#### Option 1: Full Docker (Production-like)
All services run in Docker containers.

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec django-backend python manage.py migrate
docker-compose exec django-backend python manage.py createsuperuser

# Collect static files
docker-compose exec django-backend python manage.py collectstatic --noinput
```

#### Option 2: Local Development (Recommended for Development)
Infrastructure in Docker, Django/FastAPI on host for hot reload and debugging.

```bash
# Start infrastructure only (PostgreSQL, Redis, RabbitMQ, Nginx)
docker-compose -f docker-compose.local.yml up -d

# Run migrations
python manage.py migrate
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Start services on host
.\start_all.bat  # Windows
# OR
./start_all.sh   # Linux/Mac
```


### Access Points

With nginx reverse proxy:

- **Main Application**: http://localhost
- **Django Admin**: http://localhost/admin
- **WebSocket Test**: http://localhost/ws-test
- **FastAPI Docs**: http://localhost/api/ai/docs
- **RabbitMQ UI**: http://localhost/rabbitmq
- **Health Check**: http://localhost/health

Direct service access (specific paths):
- **Django Admin**: http://localhost:8001/admin/
- **Django WebSocket Test**: http://localhost:8001/ws-test/
- **FastAPI Docs**: http://localhost:8000/docs
- **Flower Dashboard**: http://localhost:5555
- **RabbitMQ Management**: http://localhost:15672

---

## 🧪 Testing WebSocket Real-Time Updates

1. Open the WebSocket test page: http://localhost:8001/ws-test/
2. Create a new application in Django admin
3. Watch real-time updates as the AI analysis completes
4. Admin interface auto-refreshes when tasks finish

---

## 📦 Technology Stack

### Backend
- **Django 5.2** + **Django Channels**: Web framework, WebSocket support
- **Daphne**: ASGI server for WebSocket
- **FastAPI**: LLM integration microservice
- **Celery**: Distributed task queue
- **PostgreSQL + pgvector**: Vector database

### AI/ML
- **Sentence Transformers**: Embedding generation
- **Ollama** / **OpenAI**: LLM providers
- **PyPDF2**: PDF text extraction

### Infrastructure
- **Docker & Docker Compose**: Containerization
- **Nginx**: Reverse proxy & load balancer
- **RabbitMQ**: Message broker
- **Redis**: Result backend & WebSocket channel layer
- **Flower**: Celery monitoring

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
