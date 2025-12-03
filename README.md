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

### 🤖 **Multi-Agent Orchestration** ⭐
- **LangGraph workflow**: Sophisticated multi-agent coordination
- **Specialized agents**: Retriever, Analyzer, Interviewer
- **Tool-calling**: Database queries, email generation, scheduling
- **Hybrid search**: Vector + keyword retrieval with intelligent ranking
- **Execution tracing**: Full visibility into agent decisions
- **Multi-dimensional scoring**: Technical, experience, culture fit analysis

### 🛡️ **Safety Guardrails** 🆕
- **PII Detection**: Automatic detection of personally identifiable information (emails, phones, names, locations)
  - Microsoft Presidio integration for enterprise-grade detection
  - Regex fallback for offline operation
- **Bias Detection**: Identifies potential bias in job descriptions and AI outputs
  - Protected categories: age, gender, race, disability, religion, appearance
  - Severity levels: low, medium, high
- **Toxicity Filtering**: ML-based detection of toxic or inappropriate content
  - Detoxify model with multi-dimensional scoring
  - Configurable threshold (default: 0.7)
- **Output Validation**: Ensures AI outputs meet quality standards
  - Pydantic schema validation
  - Content quality checks (no placeholders, repetition, generic content)
- **Safety Reporting**: Visual safety reports in Django admin with dark theme
  - Integrated into all AI workflows (screening, multi-agent analysis)
  - Real-time safety issue detection and logging

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

# Download spaCy model for PII detection
python -m spacy download en_core_web_lg
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
- **Multi-Agent Analysis**: http://localhost/api/ai/agent/analyze ⭐ **NEW**
- **RabbitMQ UI**: http://localhost/rabbitmq
- **Health Check**: http://localhost/health

Direct service access (specific paths):
- **Django Admin**: http://localhost:8001/admin/
- **Django WebSocket Test**: http://localhost:8001/ws-test/
- **FastAPI Docs**: http://localhost:8000/docs
- **FastAPI Agent Docs**: http://localhost:8000/agent/analyze ⭐ **NEW**
- **Flower Dashboard**: http://localhost:5555
- **RabbitMQ Management**: http://localhost:15672

Monitoring stack:
- **Grafana Dashboards**: http://localhost/grafana (admin/admin)
- **Prometheus**: http://localhost/prometheus
- **Prometheus Targets**: http://localhost/prometheus/targets

---

## 📊 Monitoring & Observability

The platform includes a **production-grade monitoring stack** with pre-configured Grafana dashboards:

### Grafana Dashboard: "Recruitment Platform - Overview"

Access at: **http://localhost/grafana** (login: `admin` / `admin`)

**Panels include:**
- **System Health**: CPU, memory, disk usage
- **Application Metrics**: Request rates, response times, error rates
- **Database Performance**: Query latency, connection pool stats
- **Celery Tasks**: Task throughput, queue lengths, worker status
- **AI/ML Metrics**: Embedding generation rate, LLM analysis duration
- **WebSocket Connections**: Active connections, message throughput

### Prometheus Metrics

Access at: **http://localhost/prometheus**

**Key metrics exported:**
- Django application metrics (via `django-prometheus`)
- PostgreSQL metrics (via `postgres_exporter`)
- Celery metrics (via `celery-exporter`)
- RabbitMQ metrics (via built-in exporter)
- Custom AI/ML metrics (embedding generation, LLM calls)

### Loki Log Aggregation

Logs from all services are collected by **Promtail** and sent to **Loki** for centralized log aggregation. View logs in Grafana's Explore tab.

---

## 🔍 LangSmith Observability

Track and debug LLM interactions with **LangSmith** tracing.

**Setup:** Add to `.env`:
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_api_key
LANGCHAIN_PROJECT=recruitment-agent
```

**What's Traced:**
- Single-LLM analysis (`/analyze`)
- Multi-agent workflows (`/agent/analyze`)
- Individual agent executions and tool calls

**Access:** Visit [smith.langchain.com](https://smith.langchain.com/) to view traces, performance metrics, and debug LLM interactions.

---

## 🛡️ Safety Guardrails Usage

Safety guardrails are automatically integrated into all AI workflows. To see safety reports:

1. **Django Admin**: Navigate to Applications → Select an application → View "AI Analysis" section
2. **Safety Report Display**: Shows PII findings, bias issues, toxicity scores, and validation errors
3. **Multi-Agent Analysis**: Safety checks run automatically on all agent outputs

### Example Safety Report

```
⚠️ Safety Guardrails Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Summary: 3 PII entities detected; 4 potential bias issues

🔒 PII Detected (3 entities)
  • PERSON (confidence: 85%)
  • EMAIL_ADDRESS (confidence: 95%)
  • PHONE_NUMBER (confidence: 88%)

⚖️ Bias Detected (4 issues)
  • Age: 'junior' (medium)
  • Age: 'energetic' (medium)
  • Gender: 'he' (high)
  • Gender: 'his' (high)
```

### Configuration

Safety guardrails can be configured in `app/guardrails/safety.py`:

- **PII Mode**: `flag` (detect only) or `redact` (replace with placeholders)
- **Toxicity Threshold**: Default 0.7 (0.0-1.0 scale)
- **LLM Bias Detection**: Optional LLM-based implicit bias detection (disabled by default for performance)

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
- **LangGraph**: Multi-agent orchestration ⭐
- **LangChain**: LLM framework and tool-calling ⭐
- **Presidio**: PII detection 🆕
- **Detoxify**: Toxicity filtering 🆕

### Infrastructure
- **Docker & Docker Compose**: Containerization
- **Nginx**: Reverse proxy & load balancer
- **RabbitMQ**: Message broker
- **Redis**: Result backend & WebSocket channel layer
- **Flower**: Celery monitoring

### Monitoring Stack
- **Prometheus**: Metrics collection and time-series database
- **Grafana**: Visualization and dashboards
- **Loki**: Log aggregation
- **Promtail**: Log shipping
- **Exporters**: postgres_exporter, celery-exporter

---

## 📝 License

This project is licensed under the MIT License.
