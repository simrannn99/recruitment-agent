# AI Recruitment Platform - Technical Overview

**From an AI Software Engineer's Perspective**

A production-ready AI recruitment platform combining **semantic vector search**, **LLM-powered resume analysis**, and **asynchronous task processing** to automate candidate screening and matching at scale.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [AI/ML Architecture](#aiml-architecture)
3. [System Architecture](#system-architecture)
4. [Technology Stack](#technology-stack)
5. [Core AI Components](#core-ai-components)
6. [Vector Search Implementation](#vector-search-implementation)
7. [LLM Integration](#llm-integration)
8. [WebSocket Real-Time Updates](#websocket-real-time-updates)
9. [Background Job Processing](#background-job-processing)
10. [Monitoring Stack](#monitoring-stack)
11. [Database Schema](#database-schema)
12. [API Design](#api-design)
13. [Deployment Strategy](#deployment-strategy)
14. [Performance & Scalability](#performance--scalability)
15. [Future AI Enhancements](#future-ai-enhancements)

---

## Executive Summary

### Problem Statement
Traditional recruitment processes face critical challenges:
- **Manual Screening**: Hours spent reviewing each resume
- **Inconsistent Evaluation**: Subjective criteria and human bias
- **Poor Candidate Matching**: Keyword-based search misses semantic similarities
- **Scalability Issues**: Unable to handle high application volumes
- **No Intelligent Insights**: Lack of automated skill gap analysis and interview preparation

### AI-Powered Solution
This platform leverages modern AI/ML techniques to revolutionize recruitment:

#### 🧠 **Semantic Vector Search**
- **Sentence Transformers** (`all-MiniLM-L6-v2`) for generating 384-dimensional embeddings
- **pgvector** extension for efficient similarity search in PostgreSQL
- **Cosine similarity** matching for finding semantically similar candidates/jobs
- **Automatic embedding regeneration** on content updates via Django signals

#### 🤖 **LLM-Powered Analysis**
- **Flexible LLM backend**: Ollama (local, free) or OpenAI (cloud, paid)
- **Structured output** with match scores, skill gaps, and interview questions
- **Async processing** via Celery for non-blocking user experience
- **Retry logic** and error handling for robust LLM interactions

#### 🔌 **WebSocket Real-Time Updates**
- **Django Channels** for WebSocket support with Daphne ASGI server
- **Real-time task notifications** for background job completion (embeddings, AI analysis)
- **Auto-refresh admin interface** when analysis completes
- **Redis channel layer** for message broadcasting across workers
- **Automatic reconnection** with exponential backoff
- **Fallback polling** for legacy browsers or connection issues

#### ⚡ **Event-Driven Architecture**
- **Django signals** trigger embedding generation on model save
- **Celery task queues** with priority-based routing
- **Real-time monitoring** via Flower dashboard
- **Horizontal scalability** with distributed workers

### Technical Highlights
- **Microservices**: FastAPI (AI) + Django (Business Logic)
- **Vector Database**: PostgreSQL with pgvector extension
- **Embedding Model**: Sentence Transformers (384-dim)
- **LLM Providers**: Ollama (llama3.2) / OpenAI (gpt-4o-mini)
- **Task Queue**: Celery + RabbitMQ + Redis
- **Real-Time Updates**: Django Channels + WebSocket + Daphne ASGI
- **Containerization**: Docker Compose with health checks

---

## AI/ML Architecture

### High-Level AI Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    AI/ML Processing Pipeline                 │
└─────────────────────────────────────────────────────────────┘

1. EMBEDDING GENERATION (Sentence Transformers)
   ┌──────────────┐
   │ Resume/Job   │──► Text Extraction ──► Sentence Transformer
   │  Document    │                        (all-MiniLM-L6-v2)
   └──────────────┘                               │
                                                  ▼
                                        384-dim Vector Embedding
                                                  │
                                                  ▼
                                        Store in PostgreSQL (pgvector)

2. SEMANTIC SEARCH (Vector Similarity)
   ┌──────────────┐
   │ Query Vector │──► Cosine Distance ──► Top-K Results
   │ (Job/Resume) │     (pgvector <=>)     (Similarity Score)
   └──────────────┘

3. LLM ANALYSIS (Resume Screening)
   ┌──────────────┐
   │ Resume Text  │──► Structured Prompt ──► LLM (Ollama/OpenAI)
   │ + Job Desc   │                                 │
   └──────────────┘                                 ▼
                                          JSON Response:
                                          - Match Score (0-100)
                                          - Skill Gaps
                                          - Interview Questions
```

### AI Component Interaction

```mermaid
graph TB
    A[User Uploads Resume] --> B[Django Signal Triggered]
    B --> C[Celery Task: Extract Text]
    C --> D[Sentence Transformer Service]
    D --> E[Generate 384-dim Embedding]
    E --> F[Store in PostgreSQL pgvector]
    
    G[User Views Job] --> H[Fetch Job Embedding]
    H --> I[Vector Similarity Search]
    I --> J[Return Top Matching Candidates]
    
    K[Application Created] --> L[Celery Task: AI Analysis]
    L --> M{LLM Provider}
    M -->|Local| N[Ollama llama3.2]
    M -->|Cloud| O[OpenAI gpt-4o-mini]
    N --> P[Structured Analysis]
    O --> P
    P --> Q[Save to Database]
```

---

## System Architecture

### Microservices Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer (Future)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼─────┐    ┌─────▼──────┐   ┌────▼──────┐
   │ FastAPI  │    │   Django   │   │  Celery   │
   │ Service  │◄───┤  Backend   │◄──┤  Workers  │
   │  (8000)  │HTTP│   (8001)   │MSG│(Background)│
   └────┬─────┘    └─────┬──────┘   └────┬──────┘
        │                │                │
        │          ┌─────▼──────┐         │
        │          │PostgreSQL  │         │
        │          │+ pgvector  │         │
        │          │   (5432)   │         │
        │          └────────────┘         │
        │                                 │
        └─────────────┬───────────────────┘
                      │
        ┌─────────────▼──────────────┐
        │   Message Queue Layer      │
        │  ┌──────────┐ ┌─────────┐ │
        │  │RabbitMQ  │ │  Redis  │ │
        │  │  (5672)  │ │ (6379)  │ │
        │  └──────────┘ └─────────┘ │
        └────────────────────────────┘
                      │
                ┌─────▼─────┐
                │  Flower   │
                │  (5555)   │
                └───────────┘
```

### Service Responsibilities

#### **FastAPI Service** (Port 8000)
- **LLM Integration**: Communicates with Ollama/OpenAI
- **Resume Analysis**: Structured prompt engineering
- **JSON Validation**: Pydantic models for type safety
- **Error Handling**: Retry logic and fallback strategies

#### **Django Backend** (Port 8001)
- **Business Logic**: CRUD operations for jobs/candidates
- **Admin Interface**: Custom UI with AI-powered matching displays
- **Signal Handlers**: Trigger embedding generation on save
- **Vector Search**: pgvector queries for semantic matching
- **REST API**: Endpoints for candidate/job search

#### **Celery Workers** (Background)
- **High Priority Queue**: Email notifications
- **Embeddings Queue**: Vector generation (fast, shouldn't block)
- **Medium Priority Queue**: LLM analysis (slow, uses Ollama)
- **Low Priority Queue**: Maintenance tasks

#### **Nginx Reverse Proxy** (Port 80)
- **Unified Entry Point**: Single port (80) for all services
- **Request Routing**: Intelligent path-based routing to backend services
- **WebSocket Support**: Upgrade handling for Django Channels
- **Static File Serving**: Efficient delivery of static/media files
- **Load Balancing**: Ready for horizontal scaling (future)
- **Security Headers**: XSS protection, frame options, content-type sniffing prevention

---

## Nginx Reverse Proxy

### Overview

Nginx serves as the **unified entry point** for the entire platform, providing a single port (80) for all services while intelligently routing requests to the appropriate backend services. This architecture simplifies deployment, enables future load balancing, and provides a production-ready setup for the recruitment platform.

### Architecture

```mermaid
graph TB
    Client[Client Browser] -->|HTTP/WS :80| Nginx[Nginx Reverse Proxy]
    
    Nginx -->|/| Django[Django Backend :8001]
    Nginx -->|/ws/| Django
    Nginx -->|/api/ai/| FastAPI[FastAPI Service :8000]
    Nginx -->|/rabbitmq/| RabbitMQ[RabbitMQ UI :15672]
    Nginx -->|/static/| StaticFiles[Static Files Volume]
    Nginx -->|/media/| MediaFiles[Media Files Volume]
    
    Django -->|WebSocket| Channels[Django Channels + Daphne]
    Django -->|Database| PostgreSQL[(PostgreSQL + pgvector)]
    FastAPI -->|LLM| Ollama[Ollama/OpenAI]
    
    style Nginx fill:#2ecc71,stroke:#27ae60,stroke-width:3px
    style Django fill:#3498db,stroke:#2980b9
    style FastAPI fill:#e74c3c,stroke:#c0392b
    style Channels fill:#9b59b6,stroke:#8e44ad
```

### Deployment Modes

The platform supports two nginx configurations for different deployment scenarios:

#### **Production Mode** (`nginx.conf`)
All services run in Docker containers with internal networking.

```nginx
upstream django_backend {
    server django-backend:8001;  # Docker service name
}

upstream fastapi_service {
    server fastapi-service:8000;  # Docker service name
}
```

**Docker Compose Configuration**:
```yaml
nginx:
  image: nginx:alpine
  container_name: recruitment-nginx
  ports:
    - "80:80"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - staticfiles:/app/staticfiles
    - media:/app/media
    - nginx_logs:/var/log/nginx
  depends_on:
    - django-backend
    - fastapi-service
```

#### **Local Development Mode** (`nginx.local.conf`)
Infrastructure in Docker, Django/FastAPI on host for hot reload and debugging.

```nginx
upstream django_backend {
    server host.docker.internal:8001;  # Host machine
}

upstream fastapi_service {
    server host.docker.internal:8000;  # Host machine
}

upstream rabbitmq_management {
    server recruitment-rabbitmq-local:15672;  # Docker service
}
```

**Docker Compose Configuration**:
```yaml
nginx:
  image: nginx:alpine
  container_name: recruitment-nginx-local
  ports:
    - "80:80"
  volumes:
    - ./nginx/nginx.local.conf:/etc/nginx/nginx.conf:ro
    - ./staticfiles:/app/staticfiles
    - ./media:/app/media
  extra_hosts:
    - "host.docker.internal:host-gateway"  # Enable host access
```

### Routing Configuration

#### **1. Django Admin & API** (`/`)

```nginx
location / {
    proxy_pass http://django_backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_redirect off;
    
    # Timeouts for long-running requests
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
}
```

**Routes**:
- `http://localhost/` → Django homepage
- `http://localhost/admin/` → Django admin interface
- `http://localhost/ws-test/` → WebSocket test page

#### **2. WebSocket Support** (`/ws/`)

```nginx
location /ws/ {
    proxy_pass http://django_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket timeouts (7 days for long-lived connections)
    proxy_connect_timeout 7d;
    proxy_send_timeout 7d;
    proxy_read_timeout 7d;
}
```

**Key Features**:
- **Protocol Upgrade**: `Upgrade: websocket` header support
- **Long-lived Connections**: 7-day timeout for persistent WebSocket connections
- **HTTP/1.1 Required**: WebSocket requires HTTP/1.1 protocol

**WebSocket URL**: `ws://localhost/ws/tasks/<task_id>/`

#### **3. FastAPI Service** (`/api/ai/`)

```nginx
location /api/ai/ {
    proxy_pass http://fastapi_service/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Longer timeout for AI processing
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
}
```

**Routes**:
- `http://localhost/api/ai/docs` → FastAPI Swagger documentation
- `http://localhost/api/ai/analyze` → LLM resume analysis endpoint

**Note**: The trailing slash in `proxy_pass http://fastapi_service/;` removes `/api/ai/` from the forwarded path.

#### **4. Static Files** (`/static/`)

```nginx
location /static/ {
    alias /app/staticfiles/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

**Features**:
- **Direct File Serving**: Nginx serves files without hitting Django
- **Long Cache**: 30-day expiration for performance
- **Immutable Cache**: Files never change (versioned filenames)

#### **5. Media Files** (`/media/`)

```nginx
location /media/ {
    alias /app/media/;
    expires 7d;
    add_header Cache-Control "public";
}
```

**Features**:
- **User Uploads**: Resumes, profile pictures, etc.
- **Shorter Cache**: 7-day expiration (files may change)

#### **6. RabbitMQ Management UI** (`/rabbitmq/`)

```nginx
location /rabbitmq/ {
    rewrite ^/rabbitmq/(.*)$ /$1 break;
    proxy_pass http://rabbitmq_management/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_redirect off;
}
```

**URL Rewriting**:
- Client: `http://localhost/rabbitmq/api/overview`
- Forwarded: `http://rabbitmq:15672/api/overview`

#### **7. Health Check** (`/health`)

```nginx
location /health {
    access_log off;
    return 200 "healthy\n";
    add_header Content-Type text/plain;
}
```

**Features**:
- **No Logging**: Prevents log spam from monitoring tools
- **Instant Response**: No backend dependency
- **Load Balancer Ready**: Standard health check endpoint

### Performance Optimizations

#### **Gzip Compression**

```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript 
           application/json application/javascript application/xml+rss 
           application/rss+xml font/truetype font/opentype 
           application/vnd.ms-fontobject image/svg+xml;
```

**Benefits**:
- **60-80% size reduction** for text-based content
- **Faster page loads** over slow connections
- **Reduced bandwidth costs**

#### **Connection Optimization**

```nginx
sendfile on;           # Zero-copy file transfer
tcp_nopush on;         # Send headers in one packet
tcp_nodelay on;        # Don't buffer data
keepalive_timeout 65;  # Reuse connections
```

#### **Worker Configuration**

```nginx
worker_processes auto;  # One worker per CPU core
worker_connections 1024;  # 1024 concurrent connections per worker
```

**Capacity**: `auto * 1024` concurrent connections (e.g., 8192 on 8-core machine)

### Security Headers

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
```

| Header | Purpose | Protection |
|--------|---------|------------|
| `X-Frame-Options` | Prevent clickjacking | Blocks embedding in iframes (except same origin) |
| `X-Content-Type-Options` | Prevent MIME sniffing | Forces browser to respect `Content-Type` |
| `X-XSS-Protection` | Enable XSS filter | Browser-level XSS attack prevention |

### Request Size Limits

```nginx
client_max_body_size 100M;
```

**Purpose**: Allow large resume uploads (PDFs, DOCX files up to 100MB)

### Logging

```nginx
log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                '$status $body_bytes_sent "$http_referer" '
                '"$http_user_agent" "$http_x_forwarded_for"';

access_log /var/log/nginx/access.log main;
error_log /var/log/nginx/error.log warn;
```

**Log Location** (Docker volume):
- Production: `nginx_logs` volume
- Local: `nginx_logs_local` volume

**Access Logs**:
```
172.18.0.1 - - [30/Nov/2025:14:30:15 +0000] "GET /admin/ HTTP/1.1" 200 5234 "-" "Mozilla/5.0"
172.18.0.1 - - [30/Nov/2025:14:30:16 +0000] "POST /api/ai/analyze HTTP/1.1" 200 1523 "-" "python-requests/2.31.0"
```

### Access Points Summary

| Service | Nginx Route | Direct Access | Purpose |
|---------|-------------|---------------|---------|
| **Django Admin** | `http://localhost/admin` | `http://localhost:8001/admin/` | Admin interface |
| **WebSocket Test** | `http://localhost/ws-test` | `http://localhost:8001/ws-test/` | WebSocket testing |
| **FastAPI Docs** | `http://localhost/api/ai/docs` | `http://localhost:8000/docs` | API documentation |
| **RabbitMQ UI** | `http://localhost/rabbitmq` | `http://localhost:15672` | Message queue monitoring |
| **Flower Dashboard** | N/A | `http://localhost:5555` | Celery task monitoring |
| **Health Check** | `http://localhost/health` | N/A | Load balancer health |

### Future Enhancements

#### **Load Balancing**

```nginx
upstream django_backend {
    least_conn;  # Route to least busy server
    server django-backend-1:8001;
    server django-backend-2:8001;
    server django-backend-3:8001;
}
```

#### **SSL/TLS Termination**

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
}
```

#### **Rate Limiting**

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /api/ai/ {
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://fastapi_service/;
}
```

---

## Core AI Components

### 1. Embedding Service

**File**: `recruitment/services/embedding_service.py`

```python
class EmbeddingService:
    """Generate semantic embeddings using Sentence Transformers."""
    
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        # Model specs:
        # - Dimensions: 384
        # - Max sequence length: 256 tokens
        # - Performance: ~14K sentences/sec on CPU
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate 384-dimensional embedding vector."""
        embedding = self.model.encode(text)
        return embedding.tolist()  # Convert numpy to list
```

**Key Features**:
- **Model**: `all-MiniLM-L6-v2` (lightweight, fast, good quality)
- **Dimensions**: 384 (balance between quality and storage)
- **Normalization**: L2 normalized for cosine similarity
- **Caching**: Embeddings stored in database to avoid recomputation

### 2. Vector Search Implementation

**File**: `recruitment/views/search_views.py`

```python
def _vector_search_candidates(
    query_embedding: List[float],
    limit: int = 10,
    similarity_threshold: float = 0.0
) -> List[Dict]:
    """Perform cosine similarity search using pgvector."""
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                id, name, email, resume_file,
                1 - (resume_embedding <=> %s::vector) AS similarity_score
            FROM recruitment_candidate
            WHERE resume_embedding IS NOT NULL
            AND 1 - (resume_embedding <=> %s::vector) >= %s
            ORDER BY resume_embedding <=> %s::vector
            LIMIT %s
        """, [query_embedding, query_embedding, similarity_threshold, 
              query_embedding, limit])
```

**pgvector Operators**:
- `<=>` : Cosine distance (0 = identical, 2 = opposite)
- `1 - distance` : Convert to similarity score (0-1 range)
- **Index**: IVFFlat index for fast approximate search

### 3. LLM Integration

**File**: `app/screening_service.py`

```python
class ResumeScreeningService:
    """Analyze resumes using LLM (Ollama or OpenAI)."""
    
    async def analyze(self, job_description: str, resume_text: str):
        """Generate structured analysis with retry logic."""
        
        prompt = self._build_prompt(job_description, resume_text)
        
        # Try LLM with retries
        for attempt in range(3):
            try:
                response = await self.llm_client.generate(prompt)
                return self._parse_response(response)
            except Exception as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

**Structured Output**:
```json
{
  "match_score": 85,
  "summary": "Strong Python and Django experience...",
  "missing_skills": ["Kubernetes", "AWS"],
  "interview_questions": [
    "Explain your Django ORM optimization experience",
    "How would you design a scalable microservices architecture?"
  ]
}
```

---

## Vector Search Implementation

### Database Schema (pgvector)

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Candidate table with embedding
CREATE TABLE recruitment_candidate (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    resume_file VARCHAR(255),
    resume_text_cache TEXT,
    resume_embedding vector(384),  -- 384-dimensional vector
    embedding_generated_at TIMESTAMP,
    created_at TIMESTAMP
);

-- Create IVFFlat index for fast similarity search
CREATE INDEX idx_candidate_embedding 
ON recruitment_candidate 
USING ivfflat (resume_embedding vector_cosine_ops)
WITH (lists = 100);

-- Job posting table with embedding
CREATE TABLE recruitment_jobposting (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    description TEXT,
    description_embedding vector(384),
    embedding_generated_at TIMESTAMP,
    created_at TIMESTAMP
);

CREATE INDEX idx_job_embedding 
ON recruitment_jobposting 
USING ivfflat (description_embedding vector_cosine_ops)
WITH (lists = 100);
```

### Embedding Generation Pipeline

```mermaid
sequenceDiagram
    participant User
    participant Django
    participant Signal
    participant Celery
    participant Transformer
    participant DB

    User->>Django: Upload Resume
    Django->>DB: Save Candidate
    DB-->>Signal: post_save triggered
    Signal->>Celery: Queue embedding task
    Celery->>Transformer: Generate embedding
    Transformer-->>Celery: 384-dim vector
    Celery->>DB: Update resume_embedding
    DB-->>Django: Embedding ready
    Django-->>User: Success (non-blocking)
```

### Search API Endpoints

#### **Search Candidates for Job**
```http
POST /api/search/candidates/
Content-Type: application/json

{
  "job_id": 1,
  "limit": 10,
  "similarity_threshold": 0.7
}
```

**Response**:
```json
{
  "query": {"job_id": 1, "title": "Senior Python Developer"},
  "results": [
    {
      "id": 5,
      "name": "Alice Johnson",
      "email": "alice@example.com",
      "similarity_score": 0.92,
      "embedding_generated_at": "2025-11-29T10:00:00Z"
    }
  ],
  "count": 10
}
```

#### **Search Jobs for Candidate**
```http
POST /api/search/jobs/
Content-Type: application/json

{
  "candidate_id": 5,
  "limit": 10,
  "similarity_threshold": 0.7
}
```

---

## LLM Integration

### Multi-Provider Architecture

```python
# Environment configuration
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')  # 'ollama' or 'openai'

if LLM_PROVIDER == 'ollama':
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')
else:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
```

### Prompt Engineering

**System Prompt**:
```
You are an expert technical recruiter analyzing resumes for job positions.
Provide structured, objective analysis based solely on the resume content.
```

**User Prompt Template**:
```
JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME:
{resume_text}

Analyze this candidate's fit for the position. Provide:
1. Match score (0-100)
2. 2-sentence summary
3. List of missing skills
4. 3 specific interview questions

Format as JSON: {{"match_score": int, "summary": str, ...}}
```

### Response Parsing & Validation

```python
from pydantic import BaseModel, Field

class ScreeningResponse(BaseModel):
    match_score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=10, max_length=500)
    missing_skills: List[str] = Field(default_factory=list)
    interview_questions: List[str] = Field(min_length=3, max_length=3)
```

---

## WebSocket Real-Time Updates

### Overview

The platform implements **WebSocket-based real-time updates** using Django Channels to provide instant feedback when background tasks complete. This eliminates the need for manual page refreshes and creates a responsive, modern user experience.

### Architecture

```mermaid
sequenceDiagram
    participant User
    participant Django
    participant Daphne
    participant Redis
    participant Celery
    participant WebSocket

    User->>Django: Create Application
    Django->>Celery: Queue AI Analysis Task
    Django-->>User: Return Task ID
    User->>Daphne: Connect WebSocket (task_id)
    Daphne->>Redis: Subscribe to task channel
    
    Celery->>Celery: Process AI Analysis
    Celery->>Redis: Publish "started" event
    Redis->>Daphne: Broadcast to subscribers
    Daphne->>WebSocket: Send "started" notification
    WebSocket-->>User: Show "Analysis started"
    
    Celery->>Celery: Complete Analysis
    Celery->>Redis: Publish "completed" event
    Redis->>Daphne: Broadcast to subscribers
    Daphne->>WebSocket: Send "completed" notification
    WebSocket-->>User: Auto-refresh page
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **ASGI Server** | Daphne | WebSocket protocol support |
| **WebSocket Framework** | Django Channels 4.0+ | WebSocket routing and consumers |
| **Channel Layer** | Redis (channels-redis) | Message broadcasting across workers |
| **Client Library** | Native WebSocket API | Browser-side WebSocket connection |

### Implementation Details

#### 1. ASGI Configuration

**File**: `recruitment_backend/asgi.py`

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from recruitment_backend.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruitment_backend.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

#### 2. WebSocket Routing

**File**: `recruitment_backend/routing.py`

```python
from django.urls import re_path
from recruitment.consumers import TaskStatusConsumer

websocket_urlpatterns = [
    re_path(r'ws/tasks/(?P<task_id>[\w-]+)/$', TaskStatusConsumer.as_asgi()),
]
```

**URL Pattern**: `ws://localhost:8001/ws/tasks/<task_id>/`

#### 3. WebSocket Consumer

**File**: `recruitment/consumers.py`

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class TaskStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.room_group_name = f'task_{self.task_id}'
        
        # Join task-specific channel group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': f'Connected to task {self.task_id}',
            'task_id': self.task_id
        }))
    
    async def disconnect(self, close_code):
        # Leave channel group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def task_update(self, event):
        # Send task update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'task_update',
            'task_id': event['task_id'],
            'status': event['status'],
            'result': event.get('result'),
            'error': event.get('error'),
            'progress': event.get('progress'),
            'timestamp': event.get('timestamp')
        }))
```

#### 4. Celery Integration

**File**: `recruitment/utils/websocket_utils.py`

```python
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime

def send_task_update(task_id, status, result=None, error=None, progress=None):
    """
    Send task status update via WebSocket.
    
    Args:
        task_id: Celery task ID
        status: 'started', 'completed', 'failed', 'progress'
        result: Task result data (optional)
        error: Error message if failed (optional)
        progress: Progress percentage 0-100 (optional)
    """
    channel_layer = get_channel_layer()
    room_group_name = f'task_{task_id}'
    
    message = {
        'type': 'task_update',
        'task_id': task_id,
        'status': status,
        'timestamp': datetime.now().isoformat()
    }
    
    if result:
        message['result'] = result
    if error:
        message['error'] = error
    if progress is not None:
        message['progress'] = progress
    
    async_to_sync(channel_layer.group_send)(
        room_group_name,
        message
    )
```

**Usage in Celery Tasks**:

```python
from recruitment.utils.websocket_utils import send_task_update

@shared_task(bind=True)
def analyze_application_async(self, application_id):
    task_id = self.request.id
    
    # Send "started" notification
    send_task_update(task_id, 'started', result={
        'application_id': application_id,
        'type': 'ai_analysis'
    })
    
    try:
        # Perform AI analysis
        result = analyze_application(application_id)
        
        # Send "completed" notification
        send_task_update(task_id, 'completed', result={
            'application_id': application_id,
            'ai_score': result['match_score'],
            'status': 'success'
        })
        
        return result
    except Exception as e:
        # Send "failed" notification
        send_task_update(task_id, 'failed', error=str(e))
        raise
```

#### 5. Admin Interface Integration

**File**: `recruitment/templates/admin/recruitment/application/change_list.html`

```html
{% extends "admin/change_list.html" %}

{% block extrahead %}
{{ block.super }}
<script>
(function() {
    // Extract task ID from URL fragment (#task=abc-123)
    const hash = window.location.hash;
    if (hash.startsWith('#task=')) {
        const taskId = hash.substring(6);
        
        // Connect to WebSocket
        const ws = new WebSocket(`ws://${window.location.host}/ws/tasks/${taskId}/`);
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.status === 'completed') {
                // Show notification and refresh page
                alert('✅ AI Analysis completed!');
                setTimeout(() => window.location.reload(), 1500);
            }
        };
    }
})();
</script>
{% endblock %}
```

#### 6. Django Settings Configuration

**File**: `recruitment_backend/settings.py`

```python
INSTALLED_APPS = [
    # ... other apps
    'channels',  # WebSocket support
]

ASGI_APPLICATION = 'recruitment_backend.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.getenv('REDIS_HOST', 'localhost'), 
                      int(os.getenv('REDIS_PORT', 6379)))],
        },
    },
}
```

### WebSocket Message Format

#### Connection Message
```json
{
  "type": "connection",
  "message": "Connected to task abc-123-def-456",
  "task_id": "abc-123-def-456"
}
```

#### Task Started
```json
{
  "type": "task_update",
  "task_id": "abc-123-def-456",
  "status": "started",
  "result": {
    "application_id": 5,
    "type": "ai_analysis"
  },
  "timestamp": "2025-11-29T18:45:00.123Z"
}
```

#### Task Completed
```json
{
  "type": "task_update",
  "task_id": "abc-123-def-456",
  "status": "completed",
  "result": {
    "application_id": 5,
    "ai_score": 85,
    "status": "success"
  },
  "timestamp": "2025-11-29T18:45:15.456Z"
}
```

#### Task Failed
```json
{
  "type": "task_update",
  "task_id": "abc-123-def-456",
  "status": "failed",
  "error": "LLM service unavailable",
  "timestamp": "2025-11-29T18:45:10.789Z"
}
```

### Client-Side Implementation

**WebSocket Test Page**: `recruitment/templates/websocket_test.html`

```javascript
class TaskMonitor {
    constructor(taskId) {
        this.taskId = taskId;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }
    
    connect() {
        this.ws = new WebSocket(`ws://${window.location.host}/ws/tasks/${this.taskId}/`);
        
        this.ws.onopen = () => {
            console.log(`✅ Connected to task ${this.taskId}`);
            this.reconnectAttempts = 0;
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onclose = (event) => {
            if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnect();
            }
        };
    }
    
    reconnect() {
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
        
        setTimeout(() => {
            console.log(`🔄 Reconnecting... (attempt ${this.reconnectAttempts})`);
            this.connect();
        }, delay);
    }
    
    handleMessage(data) {
        switch(data.status) {
            case 'started':
                console.log('🔄 Task started');
                break;
            case 'completed':
                console.log('✅ Task completed', data.result);
                break;
            case 'failed':
                console.error('❌ Task failed', data.error);
                break;
        }
    }
}

// Usage
const monitor = new TaskMonitor('abc-123-def-456');
monitor.connect();
```

### Deployment Configuration

#### Docker Compose

```yaml
services:
  django-backend:
    command: daphne -b 0.0.0.0 -p 8001 recruitment_backend.asgi:application
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
```

#### Local Development

```bash
# Start Redis
docker-compose -f docker-compose.local.yml up -d redis

# Start Django with Daphne
daphne -b 0.0.0.0 -p 8001 recruitment_backend.asgi:application
```

### Performance Considerations

| Aspect | Implementation | Benefit |
|--------|---------------|---------|
| **Connection Pooling** | Redis connection pool | Reduced latency |
| **Message Serialization** | JSON (lightweight) | Fast transmission |
| **Channel Groups** | Task-specific groups | Targeted broadcasting |
| **Automatic Cleanup** | Disconnect handler | Resource management |
| **Reconnection Logic** | Exponential backoff | Resilient connections |

### Testing

**WebSocket Test Page**: `http://localhost:8001/ws-test/`

Features:
- Connect to specific task IDs
- Real-time message display
- Connection status indicator
- Automatic reconnection
- Message history

### Future Enhancements

1. **Authentication**: Add JWT-based WebSocket authentication
2. **Batch Updates**: Support multiple task monitoring in single connection
3. **Progress Tracking**: Real-time progress bars for long-running tasks
4. **Notifications**: Browser push notifications for completed tasks
5. **Admin Dashboard**: Live task monitoring dashboard

---

## Background Job Processing

### Overview

The platform uses **Celery** as a distributed task queue to handle CPU-intensive operations asynchronously. This architecture ensures the web application remains responsive while background tasks (embedding generation, AI analysis, email notifications) are processed by dedicated workers.

### Architecture

```mermaid
graph TB
    subgraph "Django Application"
        A[Django View/Signal]
        B[Celery Task]
    end
    
    subgraph "Message Broker - RabbitMQ"
        C[High Priority Queue]
        D[Embeddings Queue]
        E[Medium Priority Queue]
        F[Low Priority Queue]
    end
    
    subgraph "Celery Workers"
        G[Worker 1]
        H[Worker 2]
        I[Worker N]
    end
    
    subgraph "Result Backend - Redis"
        J[Task Results]
        K[Task Status]
        L[Channel Layer]
    end
    
    A -->|Queue Task| B
    B -->|Route by Priority| C
    B -->|Route by Priority| D
    B -->|Route by Priority| E
    B -->|Route by Priority| F
    
    C --> G
    D --> H
    E --> I
    F --> G
    
    G -->|Store Result| J
    H -->|Store Result| J
    I -->|Store Result| J
    
    G -->|Update Status| K
    H -->|Update Status| K
    I -->|Update Status| K
    
    G -->|WebSocket Broadcast| L
    H -->|WebSocket Broadcast| L
    I -->|WebSocket Broadcast| L
```

### Component Roles

| Component | Technology | Role | Configuration |
|-----------|------------|------|---------------|
| **Message Broker** | RabbitMQ 3.13 | Queue management, task routing | 4 priority queues, durable messages |
| **Result Backend** | Redis 7 | Store task results, cache | Persistent storage, pub/sub for WebSocket |
| **Task Queue** | Celery 5.3+ | Distributed task execution | Priority routing, retry logic, monitoring |
| **Workers** | Celery Workers | Execute background tasks | Multi-queue consumption, concurrency control |

### RabbitMQ Configuration

**Purpose**: Message broker for task distribution

**Docker Configuration**:
```yaml
rabbitmq:
  image: rabbitmq:3.13-management-alpine
  container_name: recruitment-rabbitmq
  environment:
    RABBITMQ_DEFAULT_USER: guest
    RABBITMQ_DEFAULT_PASS: guest
  ports:
    - "5672:5672"    # AMQP protocol
    - "15672:15672"  # Management UI
  volumes:
    - rabbitmq_data:/var/lib/rabbitmq
  healthcheck:
    test: ["CMD", "rabbitmq-diagnostics", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Queue Structure**:
```python
# settings.py
CELERY_TASK_QUEUES = (
    Queue('high_priority', 
          routing_key='high_priority', 
          priority=10,
          queue_arguments={'x-max-priority': 10}),
    
    Queue('embeddings', 
          routing_key='embeddings', 
          priority=7,
          queue_arguments={'x-max-priority': 10}),
    
    Queue('medium_priority', 
          routing_key='medium_priority', 
          priority=5,
          queue_arguments={'x-max-priority': 10}),
    
    Queue('low_priority', 
          routing_key='low_priority', 
          priority=1,
          queue_arguments={'x-max-priority': 10}),
)
```

**Why RabbitMQ?**
- **Reliability**: Durable queues, message persistence
- **Priority Queues**: Native support for task prioritization
- **Routing**: Flexible message routing based on task type
- **Monitoring**: Built-in management UI at port 15672
- **Scalability**: Handles thousands of messages per second

### Redis Configuration

**Purpose**: Result backend + WebSocket channel layer

**Docker Configuration**:
```yaml
redis:
  image: redis:7-alpine
  container_name: recruitment-redis
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Django Configuration**:
```python
# settings.py

# Celery Result Backend
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_EXPIRES = 3600  # 1 hour

# WebSocket Channel Layer
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('localhost', 6379)],
        },
    },
}
```

**Why Redis?**
- **Speed**: In-memory storage for fast result retrieval
- **Persistence**: AOF (Append-Only File) for data durability
- **Pub/Sub**: Native support for WebSocket broadcasting
- **Dual Purpose**: Single instance for both Celery results and WebSocket
- **Lightweight**: Minimal resource footprint

### Celery Configuration

**Django Settings** (`recruitment_backend/settings.py`):

```python
import os
from kombu import Queue

# Broker Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5672//')
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Result Backend
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_EXPIRES = 3600

# Task Serialization
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'

# Task Queues with Priorities
CELERY_TASK_QUEUES = (
    Queue('high_priority', routing_key='high_priority', priority=10),
    Queue('embeddings', routing_key='embeddings', priority=7),
    Queue('medium_priority', routing_key='medium_priority', priority=5),
    Queue('low_priority', routing_key='low_priority', priority=1),
)

# Task Routing
CELERY_TASK_ROUTES = {
    'recruitment.tasks.send_application_status_email': {
        'queue': 'high_priority',
        'routing_key': 'high_priority',
    },
    'recruitment.tasks.generate_candidate_embedding_async': {
        'queue': 'embeddings',
        'routing_key': 'embeddings',
    },
    'recruitment.tasks.generate_job_embedding_async': {
        'queue': 'embeddings',
        'routing_key': 'embeddings',
    },
    'recruitment.tasks.analyze_application_async': {
        'queue': 'medium_priority',
        'routing_key': 'medium_priority',
    },
    'recruitment.tasks.batch_analyze_applications': {
        'queue': 'low_priority',
        'routing_key': 'low_priority',
    },
}

# Worker Configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # One task at a time
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100  # Restart worker after 100 tasks
CELERY_TASK_ACKS_LATE = True  # Acknowledge task after completion
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Requeue if worker dies
```

### Task Routing Strategy

| Task | Queue | Priority | Reason |
|------|-------|----------|--------|
| Email notifications | `high_priority` | 10 | User-facing, fast |
| Embedding generation | `embeddings` | 7 | Fast, shouldn't block AI analysis |
| LLM analysis | `medium_priority` | 5 | Slow, uses Ollama |
| Cleanup tasks | `low_priority` | 1 | Can wait |

### Task Execution Workflow

```mermaid
sequenceDiagram
    participant Django
    participant RabbitMQ
    participant Worker
    participant Redis
    participant WebSocket

    Django->>RabbitMQ: Queue Task (analyze_application_async)
    RabbitMQ->>Worker: Deliver Task
    Worker->>Redis: Update Status (STARTED)
    Worker->>WebSocket: Broadcast "started" event
    
    Worker->>Worker: Execute Task Logic
    Note over Worker: Call FastAPI for LLM analysis
    
    alt Task Success
        Worker->>Redis: Store Result
        Worker->>Redis: Update Status (SUCCESS)
        Worker->>WebSocket: Broadcast "completed" event
        Worker->>RabbitMQ: ACK Message
    else Task Failure
        Worker->>Redis: Store Error
        Worker->>Redis: Update Status (FAILURE)
        Worker->>WebSocket: Broadcast "failed" event
        Worker->>RabbitMQ: NACK Message (Retry)
    end
```

### Key Celery Tasks Implementation

#### 1. Embedding Generation Task

**File**: `recruitment/tasks.py`

```python
from celery import shared_task
from recruitment.utils.websocket_utils import send_task_update

@shared_task(
    bind=True,
    queue='embeddings',
    max_retries=3,
    default_retry_delay=60
)
def generate_candidate_embedding_async(self, candidate_id):
    """Generate embedding for candidate resume with WebSocket notifications."""
    task_id = self.request.id
    
    try:
        # Send "started" notification
        send_task_update(task_id, 'started', result={
            'candidate_id': candidate_id,
            'type': 'embedding_generation'
        })
        
        candidate = Candidate.objects.get(id=candidate_id)
        embedding_service = EmbeddingService()
        
        # Extract text from resume PDF
        text = extract_text_from_pdf(candidate.resume_file.path)
        
        # Generate embedding (384-dim vector)
        embedding = embedding_service.generate_embedding(text)
        
        # Save to database
        candidate.resume_embedding = embedding
        candidate.resume_text_cache = text
        candidate.embedding_generated_at = timezone.now()
        candidate.save()
        
        # Send "completed" notification
        send_task_update(task_id, 'completed', result={
            'candidate_id': candidate_id,
            'embedding_dimension': len(embedding),
            'status': 'success'
        })
        
        return {
            'candidate_id': candidate_id,
            'embedding_dimension': len(embedding),
            'status': 'success'
        }
        
    except Exception as exc:
        # Send "failed" notification
        send_task_update(task_id, 'failed', error=str(exc))
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

#### 2. AI Analysis Task

```python
@shared_task(
    bind=True,
    queue='medium_priority',
    max_retries=3,
    default_retry_delay=120
)
def analyze_application_async(self, application_id):
    """Analyze application using LLM with WebSocket notifications."""
    task_id = self.request.id
    
    try:
        # Send "started" notification
        send_task_update(task_id, 'started', result={
            'application_id': application_id,
            'type': 'ai_analysis'
        })
        
        application = Application.objects.get(id=application_id)
        
        # Call FastAPI service for LLM analysis
        response = requests.post(
            f"{AI_SERVICE_URL}/analyze",
            json={
                "job_description": application.job.description,
                "resume_text": application.candidate.resume_text_cache
            },
            timeout=AI_SERVICE_TIMEOUT
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Save analysis results
        application.ai_score = result['match_score']
        application.ai_feedback = result
        application.save()
        
        # Send "completed" notification
        send_task_update(task_id, 'completed', result={
            'application_id': application_id,
            'ai_score': result['match_score'],
            'status': 'success'
        })
        
        return result
        
    except Exception as exc:
        # Send "failed" notification
        send_task_update(task_id, 'failed', error=str(exc))
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))
```

#### 3. Email Notification Task

```python
@shared_task(
    bind=True,
    queue='high_priority',
    max_retries=5,
    default_retry_delay=30
)
def send_application_status_email(self, application_id, status):
    """Send email notification to candidate."""
    try:
        application = Application.objects.get(id=application_id)
        
        subject = f"Application Update: {application.job.title}"
        message = f"Your application status has been updated to: {status}"
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.candidate.email],
            fail_silently=False
        )
        
        return {'status': 'sent', 'recipient': application.candidate.email}
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
```

### Worker Management

**Starting Workers**:

```bash
# Single worker consuming all queues
celery -A recruitment_backend worker \
    -Q high_priority,embeddings,medium_priority,low_priority \
    -l info \
    --pool=solo  # Windows compatibility

# Multiple specialized workers (Linux/Mac)
celery -A recruitment_backend worker -Q high_priority,embeddings -n worker1@%h -c 4
celery -A recruitment_backend worker -Q medium_priority,low_priority -n worker2@%h -c 2
```

**Worker Configuration**:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `-Q` | Queue names | Specify which queues to consume |
| `-l` | Log level (info) | Logging verbosity |
| `-c` | Concurrency (4) | Number of parallel tasks |
| `-n` | Worker name | Unique identifier |
| `--pool` | solo/prefork | Execution pool type |
| `--max-tasks-per-child` | 100 | Restart after N tasks (memory management) |

### Monitoring with Flower

**Flower Dashboard**: Real-time Celery monitoring

**Starting Flower**:
```bash
celery -A recruitment_backend flower --port=5555
```

**Access**: http://localhost:5555

**Features**:
- **Task History**: View all executed tasks
- **Worker Status**: Monitor worker health and performance
- **Queue Lengths**: Track queue backlogs
- **Task Details**: Inspect arguments, results, and errors
- **Rate Limiting**: Configure task execution rates
- **Task Revocation**: Cancel running tasks

**Key Metrics**:
- Tasks processed per second
- Average task runtime
- Success/failure rates
- Worker CPU/memory usage

### Retry Logic and Error Handling

**Exponential Backoff**:
```python
# First retry: 60 seconds
# Second retry: 120 seconds (60 * 2^1)
# Third retry: 240 seconds (60 * 2^2)
countdown = base_delay * (2 ** self.request.retries)
```

**Task States**:
| State | Description | Action |
|-------|-------------|--------|
| `PENDING` | Task queued, not started | Wait for worker |
| `STARTED` | Task picked up by worker | In progress |
| `SUCCESS` | Task completed successfully | Result stored in Redis |
| `FAILURE` | Task failed after retries | Error logged |
| `RETRY` | Task failed, will retry | Requeued with delay |
| `REVOKED` | Task cancelled manually | Removed from queue |

### Task Result Storage

**Redis Key Structure**:
```
celery-task-meta-<task_id>  # Task result and metadata
celery-task-state-<task_id> # Task state (PENDING, SUCCESS, etc.)
```

**Result Expiration**: 1 hour (configurable via `CELERY_RESULT_EXPIRES`)

**Retrieving Results**:
```python
from celery.result import AsyncResult

task = analyze_application_async.delay(application_id)
result = AsyncResult(task.id)

# Check status
if result.ready():
    if result.successful():
        data = result.get()
    else:
        error = result.info  # Exception details
```

### Performance Optimization

| Strategy | Implementation | Benefit |
|----------|---------------|---------|
| **Task Routing** | Priority-based queues | Critical tasks execute first |
| **Prefetch Limit** | `PREFETCH_MULTIPLIER = 1` | Prevents worker overload |
| **Result Expiration** | 1 hour TTL | Reduces Redis memory usage |
| **Worker Restart** | Max 100 tasks per child | Prevents memory leaks |
| **Late ACK** | `TASK_ACKS_LATE = True` | Ensures task completion |
| **Connection Pooling** | Redis/RabbitMQ pools | Reduces connection overhead |

### Deployment Configuration

**Docker Compose** (`docker-compose.yml`):

```yaml
services:
  celery-worker:
    build: .
    command: celery -A recruitment_backend worker -Q high_priority,embeddings,medium_priority,low_priority -l info --pool=solo
    environment:
      - CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      rabbitmq:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./media:/app/media
    restart: unless-stopped
  
  flower:
    build: .
    command: celery -A recruitment_backend flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
    depends_on:
      - rabbitmq
    restart: unless-stopped
```

### Troubleshooting

**Common Issues**:

1. **Tasks not executing**
   - Check worker is running: `celery -A recruitment_backend inspect active`
   - Verify RabbitMQ connection: `celery -A recruitment_backend inspect ping`
   - Check queue routing: Ensure task queue matches worker queue

2. **High memory usage**
   - Reduce `CELERY_WORKER_MAX_TASKS_PER_CHILD`
   - Lower concurrency: `-c 2` instead of `-c 4`
   - Enable worker autoscaling: `--autoscale=10,3`

3. **Tasks timing out**
   - Increase `AI_SERVICE_TIMEOUT` for LLM tasks
   - Add retry logic with longer delays
   - Monitor Flower for slow tasks

4. **RabbitMQ connection errors**
   - Check RabbitMQ is running: `docker ps | grep rabbitmq`
   - Verify credentials in `CELERY_BROKER_URL`
   - Check network connectivity

**Useful Commands**:
```bash
# Inspect active tasks
celery -A recruitment_backend inspect active

# Purge all queues
celery -A recruitment_backend purge

# Revoke specific task
celery -A recruitment_backend revoke <task_id>

# Monitor events
celery -A recruitment_backend events
```

---

```python
@shared_task(queue='embeddings')
def generate_candidate_embedding_async(candidate_id):
    """Generate embedding for candidate resume."""
    candidate = Candidate.objects.get(id=candidate_id)
    embedding_service = EmbeddingService()
    
    # Extract text from resume PDF
    text = extract_text_from_pdf(candidate.resume_file.path)
    
    # Generate embedding
    embedding = embedding_service.generate_embedding(text)
    
    # Save to database
    candidate.resume_embedding = embedding
    candidate.embedding_generated_at = timezone.now()
    candidate.save()
```

---

## Monitoring Stack

### Overview

The recruitment platform implements a **production-grade observability stack** using industry-standard tools for metrics collection, log aggregation, and visualization. This enables real-time monitoring of application performance, system health, and troubleshooting of issues.

### Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        Django[Django Backend :8001]
        FastAPI[FastAPI Service :8000]
        Celery[Celery Workers]
        Nginx[Nginx :80]
    end
    
    subgraph "Metrics Collection"
        DjangoMetrics[django-prometheus]
        FastAPIMetrics[prometheus-fastapi-instrumentator]
        CeleryExporter[Celery Exporter :9808]
        PostgresExporter[Postgres Exporter :9187]
    end
    
    subgraph "Monitoring Stack"
        Prometheus[Prometheus :9090]
        Loki[Loki :3100]
        Promtail[Promtail]
        Grafana[Grafana :3000]
    end
    
    Django --> DjangoMetrics
    FastAPI --> FastAPIMetrics
    Celery --> CeleryExporter
    
    DjangoMetrics -->|/metrics| Prometheus
    FastAPIMetrics -->|/metrics| Prometheus
    CeleryExporter -->|/metrics| Prometheus
    PostgresExporter -->|/metrics| Prometheus
    
    Django -->|logs| Promtail
    FastAPI -->|logs| Promtail
    Celery -->|logs| Promtail
    Nginx -->|logs| Promtail
    
    Promtail -->|push| Loki
    Prometheus -->|query| Grafana
    Loki -->|query| Grafana
    
    style Prometheus fill:#e74c3c,stroke:#c0392b,stroke-width:2px
    style Grafana fill:#f39c12,stroke:#e67e22,stroke-width:2px
    style Loki fill:#3498db,stroke:#2980b9,stroke-width:2px
```

### Components

#### **1. Prometheus** (Metrics Collection & Storage)

**Purpose**: Time-series database for collecting and storing metrics from all services.

**Configuration** (`monitoring/prometheus.local.yml`):
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Django Backend Metrics
  - job_name: 'django'
    static_configs:
      - targets: ['host.docker.internal:8001']
    metrics_path: '/metrics'
    
  # FastAPI Service Metrics
  - job_name: 'fastapi'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
    
  # Celery Task Metrics
  - job_name: 'celery'
    static_configs:
      - targets: ['celery-exporter:9808']
    
  # PostgreSQL Database Metrics
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    
  # RabbitMQ Message Queue Metrics
  - job_name: 'rabbitmq'
    static_configs:
      - targets: ['rabbitmq:15692']
```

**Metrics Collected**:
- **Django**: Request rates, response times, error rates, active requests
- **FastAPI**: API endpoint performance, LLM call duration, error rates
- **Celery**: Task execution times, queue lengths, worker status, task success/failure rates
- **PostgreSQL**: Connection pool usage, query performance, database size
- **RabbitMQ**: Message rates, queue depths, consumer counts

**Access Points**:
- **Via Nginx**: `http://localhost/prometheus`
- **Direct**: `http://localhost:9090`
- **Targets Page**: `http://localhost/prometheus/targets` (view scrape status)
- **Graph UI**: `http://localhost/prometheus/graph` (query metrics)

#### **2. Grafana** (Visualization & Dashboards)

**Purpose**: Unified dashboard for visualizing metrics and logs from Prometheus and Loki.

**Configuration** (`monitoring/grafana/provisioning/`):
```yaml
# datasources.yml
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
```

**Pre-configured Dashboard**: **"Recruitment Platform - Overview"**

Auto-provisioned on startup from `monitoring/grafana/dashboards/recruitment-platform-overview.json`

**10 Real-time Panels:**
1. **Request Rate (req/sec)** - HTTP requests per second for Django (GET/POST) and FastAPI
2. **Response Time (p95)** - 95th percentile response latencies (gauge visualization)
3. **Celery Task Rate by State** - Success/Failure/Retry rates with task names
4. **Celery Queue Length** - Number of pending tasks per queue (gauge visualization)
5. **PostgreSQL Connections** - Active connections vs Max connections
6. **PostgreSQL Transaction Rate** - Commits and rollbacks per second
7. **Django Error Rate** - Percentage of failed requests (gauge visualization)
8. **Celery Workers** - Number of active workers
9. **Database Size** - Current database size in bytes
10. **Total Celery Tasks Processed** - Cumulative task count

**Dashboard Features:**
- ✅ **Auto-refresh**: Every 10 seconds
- ✅ **Time range**: Last 1 hour (adjustable)
- ✅ **Auto-provisioned**: Loads automatically on Grafana startup
- ✅ **Color-coded thresholds**: Green/yellow/red indicators
- ✅ **Task name labels**: Shows specific task names in Celery metrics

**Access Points**:
- **Via Nginx**: `http://localhost/grafana` (recommended)
- **Direct**: `http://localhost:3000`
- **Default Credentials**: `admin` / `admin` (change on first login)

**Key Features**:
- **Real-time Dashboards**: Auto-refreshing metrics visualization
- **Alerting**: Configure alerts for critical metrics (e.g., high error rates)
- **Log Correlation**: Click from metrics to related logs
- **Multi-datasource**: Combine Prometheus metrics with Loki logs

#### **3. Loki** (Log Aggregation)

**Purpose**: Centralized log storage and querying system (like Prometheus, but for logs).

**Configuration** (`monitoring/loki-config.yml`):
```yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 168h

storage_config:
  boltdb:
    directory: /loki/index
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
```

**Log Sources**:
- Django application logs
- FastAPI service logs
- Celery worker logs
- Nginx access/error logs

**Access**: Queried through Grafana (no direct UI)

**Query Examples** (LogQL):
```logql
# All Django errors
{job="django"} |= "ERROR"

# FastAPI slow requests (>1s)
{job="fastapi"} | json | duration > 1s

# Celery task failures
{job="celery"} |= "FAILURE"
```

#### **4. Promtail** (Log Shipper)

**Purpose**: Collects logs from files and ships them to Loki.

**Configuration** (`monitoring/promtail-config.yml`):
```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Django logs
  - job_name: django
    static_configs:
      - targets:
          - localhost
        labels:
          job: django
          __path__: /var/log/django/*.log
          
  # FastAPI logs
  - job_name: fastapi
    static_configs:
      - targets:
          - localhost
        labels:
          job: fastapi
          __path__: /var/log/fastapi/*.log
          
  # Nginx logs
  - job_name: nginx
    static_configs:
      - targets:
          - localhost
        labels:
          job: nginx
          __path__: /var/log/nginx/*.log
```

#### **5. Exporters**

**Celery Exporter** (`danihodovic/celery-exporter`):
```yaml
celery-exporter:
  image: danihodovic/celery-exporter:latest
  container_name: recruitment-celery-exporter-local
  command:
    - --broker-url=amqp://guest:guest@rabbitmq:5672//
    - --retry-interval=5
  ports:
    - "9808:9808"
  depends_on:
    rabbitmq:
      condition: service_healthy
```

**Metrics Exposed**:
- `celery_tasks_total`: Total tasks by state (SUCCESS, FAILURE, PENDING)
- `celery_task_runtime_seconds`: Task execution duration
- `celery_workers_total`: Number of active workers
- `celery_queue_length`: Messages in each queue

**PostgreSQL Exporter** (`prometheuscommunity/postgres-exporter`):
```yaml
postgres-exporter:
  image: prometheuscommunity/postgres-exporter:latest
  container_name: recruitment-postgres-exporter-local
  environment:
    DATA_SOURCE_NAME: "postgresql://recruitment_user:recruitment_pass@postgres:5432/recruitment_db?sslmode=disable"
  ports:
    - "9187:9187"
  depends_on:
    postgres:
      condition: service_healthy
```

**Metrics Exposed**:
- `pg_stat_database_*`: Database statistics (connections, transactions, etc.)
- `pg_stat_user_tables_*`: Table-level statistics
- `pg_locks_*`: Lock information
- `pg_database_size_bytes`: Database size

### Application Instrumentation

#### **Django Metrics** (`django-prometheus`)

**Installation**:
```python
# settings.py
INSTALLED_APPS = [
    'django_prometheus',
    # ... other apps
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # ... other middleware
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]
```

**URL Configuration**:
```python
# urls.py
urlpatterns = [
    path('', include('django_prometheus.urls')),  # Exposes /metrics
    # ... other patterns
]
```

**Metrics Endpoint**: `http://localhost:8001/metrics`

**Sample Metrics**:
```
# Django request duration
django_http_requests_latency_seconds_by_view_method_bucket{le="0.5",method="GET",view="admin:index"} 145

# Active requests
django_http_requests_total_by_method_total{method="POST"} 523

# Database queries
django_db_query_duration_seconds_count 1247
```

#### **FastAPI Metrics** (`prometheus-fastapi-instrumentator`)

**Installation**:
```python
# app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Enable Prometheus instrumentation
Instrumentator().instrument(app).expose(app)
```

**Metrics Endpoint**: `http://localhost:8000/metrics`

**Sample Metrics**:
```
# HTTP request duration
http_request_duration_seconds_bucket{le="1.0",method="POST",path="/analyze"} 89

# Request count
http_requests_total{method="POST",path="/analyze",status="200"} 156

# Requests in progress
http_requests_inprogress{method="POST",path="/analyze"} 3
```

### Nginx Routing for Monitoring

**Configuration** (`nginx/nginx.local.conf`):
```nginx
# Prometheus UI
location /prometheus/ {
    proxy_pass http://prometheus/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Grafana Dashboard
location /grafana/ {
    proxy_pass http://grafana/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Django Metrics
location /metrics {
    proxy_pass http://django_backend/metrics;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Prometheus Graph UI
location /graph {
    proxy_pass http://prometheus/graph;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Docker Compose Configuration

```yaml
# Prometheus
prometheus:
  image: prom/prometheus:latest
  container_name: recruitment-prometheus-local
  volumes:
    - ./monitoring/prometheus.local.yml:/etc/prometheus/prometheus.yml:ro
    - prometheus_data_local:/prometheus
  ports:
    - "9090:9090"
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
    - '--web.console.libraries=/etc/prometheus/console_libraries'
    - '--web.console.templates=/etc/prometheus/consoles'

# Grafana
grafana:
  image: grafana/grafana:latest
  container_name: recruitment-grafana-local
  volumes:
    - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
    - grafana_data_local:/var/lib/grafana
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
    - GF_USERS_ALLOW_SIGN_UP=false
    - GF_SERVER_ROOT_URL=http://localhost/grafana
    - GF_SERVER_SERVE_FROM_SUB_PATH=true
  depends_on:
    - prometheus
    - loki

# Loki
loki:
  image: grafana/loki:latest
  container_name: recruitment-loki-local
  volumes:
    - ./monitoring/loki-config.yml:/etc/loki/local-config.yaml:ro
    - loki_data_local:/loki
  ports:
    - "3100:3100"
  command: -config.file=/etc/loki/local-config.yaml

# Promtail
promtail:
  image: grafana/promtail:latest
  container_name: recruitment-promtail-local
  volumes:
    - ./monitoring/promtail-config.yml:/etc/promtail/config.yml:ro
    - ./logs:/var/log:ro
  command: -config.file=/etc/promtail/config.yml
  depends_on:
    - loki
```

### Access Summary

| Service | Via Nginx (Recommended) | Direct Access | Purpose |
|---------|------------------------|---------------|---------|
| **Grafana** | `http://localhost/grafana` | `http://localhost:3000` | Dashboards & visualization |
| **Prometheus** | `http://localhost/prometheus` | `http://localhost:9090` | Metrics database & query |
| **Prometheus Targets** | `http://localhost/prometheus/targets` | `http://localhost:9090/targets` | Scrape status monitoring |
| **Prometheus Graph** | `http://localhost/graph` | `http://localhost:9090/graph` | Metrics query UI |
| **Django Metrics** | `http://localhost/metrics` | `http://localhost:8001/metrics` | Django application metrics |
| **FastAPI Metrics** | N/A | `http://localhost:8000/metrics` | FastAPI service metrics |
| **Celery Exporter** | N/A | `http://localhost:9808/metrics` | Celery task metrics |
| **Postgres Exporter** | N/A | `http://localhost:9187/metrics` | Database metrics |

### Key Metrics to Monitor

#### **Application Health**
- **Request Rate**: `rate(http_requests_total[5m])`
- **Error Rate**: `rate(http_requests_total{status=~"5.."}[5m])`
- **Response Time (p95)**: `histogram_quantile(0.95, http_request_duration_seconds_bucket)`

#### **Celery Performance**
- **Task Success Rate**: `rate(celery_tasks_total{state="SUCCESS"}[5m])`
- **Task Failure Rate**: `rate(celery_tasks_total{state="FAILURE"}[5m])`
- **Queue Length**: `celery_queue_length`
- **Task Duration (p95)**: `histogram_quantile(0.95, celery_task_runtime_seconds_bucket)`

#### **Database Performance**
- **Active Connections**: `pg_stat_database_numbackends`
- **Transaction Rate**: `rate(pg_stat_database_xact_commit[5m])`
- **Database Size**: `pg_database_size_bytes`

#### **System Resources**
- **CPU Usage**: `rate(process_cpu_seconds_total[5m])`
- **Memory Usage**: `process_resident_memory_bytes`
- **Disk Usage**: `node_filesystem_avail_bytes`

### Alerting (Future Enhancement)

**Example Alert Rules** (`prometheus/alerts.yml`):
```yaml
groups:
  - name: application_alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} requests/sec"
      
      # Celery queue backup
      - alert: CeleryQueueBackup
        expr: celery_queue_length > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Celery queue backup detected"
          description: "Queue {{ $labels.queue }} has {{ $value }} pending tasks"
      
      # Database connection pool exhaustion
      - alert: DatabaseConnectionPoolHigh
        expr: pg_stat_database_numbackends / pg_settings_max_connections > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool usage high"
          description: "{{ $value }}% of connections in use"
```

### Troubleshooting

#### **Prometheus Not Scraping Targets**
1. Check target status: `http://localhost/prometheus/targets`
2. Verify service is exposing `/metrics` endpoint
3. Check network connectivity between Prometheus and target
4. Review Prometheus logs: `docker logs recruitment-prometheus-local`

#### **Grafana Not Showing Data**
1. Verify datasource configuration in Grafana
2. Test Prometheus connection: Grafana → Configuration → Data Sources → Test
3. Check time range in dashboard (default: last 6 hours)
4. Verify metrics exist in Prometheus: `http://localhost/prometheus/graph`

#### **Loki Logs Not Appearing**
1. Check Promtail is running: `docker ps | grep promtail`
2. Verify log file paths in `promtail-config.yml`
3. Check Promtail logs: `docker logs recruitment-promtail-local`
4. Test Loki connection from Grafana

#### **High Memory Usage**
1. Reduce Prometheus retention: `--storage.tsdb.retention.time=7d`
2. Limit Loki retention in `loki-config.yml`
3. Reduce scrape frequency in `prometheus.yml`

### Best Practices

1. **Metric Naming**: Follow Prometheus naming conventions (`<namespace>_<name>_<unit>`)
2. **Label Cardinality**: Avoid high-cardinality labels (e.g., user IDs, timestamps)
3. **Dashboard Organization**: Group related metrics, use consistent time ranges
4. **Alert Fatigue**: Set appropriate thresholds, use `for` clause to avoid flapping
5. **Log Retention**: Balance storage costs with troubleshooting needs (7-30 days typical)
6. **Regular Review**: Monitor dashboard usage, deprecate unused metrics
7. **Documentation**: Document custom metrics and their business meaning

---

```python
    # Save to database
    candidate.resume_embedding = embedding
    candidate.resume_text_cache = text
    candidate.embedding_generated_at = timezone.now()
    candidate.save()

@shared_task(queue='medium_priority')
def analyze_application_async(application_id):
    """Analyze application using LLM."""
    application = Application.objects.get(id=application_id)
    
    # Call FastAPI service
    response = requests.post(
        f"{AI_SERVICE_URL}/analyze",
        json={
            "job_description": application.job.description,
            "resume_text": application.candidate.resume_text_cache
        },
        timeout=AI_SERVICE_TIMEOUT
    )
    
    result = response.json()
    
    # Save analysis
    application.ai_score = result['match_score']
    application.ai_feedback = result
    application.save()
```

---

## Database Schema

### Core Models

```python
class Candidate(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    resume_file = models.FileField(upload_to='resumes/')
    
    # AI/ML fields
    resume_text_cache = models.TextField(null=True, blank=True)
    resume_embedding = VectorField(dimensions=384, null=True, blank=True)
    embedding_generated_at = models.DateTimeField(null=True, blank=True)
    
    @property
    def has_embedding(self):
        return self.resume_embedding is not None

class JobPosting(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # AI/ML fields
    description_embedding = VectorField(dimensions=384, null=True, blank=True)
    embedding_generated_at = models.DateTimeField(null=True, blank=True)

class Application(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # AI analysis results
    ai_score = models.IntegerField(null=True, blank=True)
    ai_feedback = models.JSONField(null=True, blank=True)
```

---

## Performance & Scalability

### Vector Search Performance

| Dataset Size | Query Time | Index Type |
|--------------|------------|------------|
| 1K candidates | ~5ms | IVFFlat (lists=100) |
| 10K candidates | ~15ms | IVFFlat (lists=100) |
| 100K candidates | ~50ms | IVFFlat (lists=1000) |
| 1M candidates | ~200ms | HNSW (m=16, ef=64) |

### Embedding Generation Performance

- **CPU**: ~100 resumes/minute (single worker)
- **GPU**: ~1000 resumes/minute (with CUDA)
- **Batch processing**: 10x faster with batch encoding

### Scaling Strategies

1. **Horizontal Scaling**: Add more Celery workers
2. **Database Sharding**: Partition by candidate ID
3. **Caching**: Redis for frequently accessed embeddings
4. **CDN**: Serve resume files from S3/CloudFront
5. **Load Balancing**: Nginx for Django/FastAPI services

---

## Future AI Enhancements

### 1. Advanced Embedding Models
- **Upgrade to larger models**: `all-mpnet-base-v2` (768-dim, better quality)
- **Domain-specific fine-tuning**: Train on recruitment data
- **Multi-modal embeddings**: Combine text + structured data

### 2. Hybrid Search
- **Combine vector + keyword search**: BM25 + cosine similarity
- **Reranking**: Use cross-encoder for top-K results
- **Filtering**: Add hard constraints (location, salary, experience)

### 3. LLM Enhancements
- **Fine-tuned models**: Train on recruitment conversations
- **RAG (Retrieval-Augmented Generation)**: Use vector search for context
- **Multi-agent systems**: Separate agents for screening, interviewing, negotiation

### 4. Explainable AI
- **Attention visualization**: Show which resume sections influenced score
- **SHAP values**: Explain feature importance
- **Counterfactual explanations**: "If candidate had X skill, score would be Y"

### 5. Active Learning
- **Feedback loop**: Learn from recruiter decisions
- **Continuous improvement**: Retrain models with new data
- **A/B testing**: Compare different embedding models

---

## Technology Stack Summary

### AI/ML Stack
- **Embedding Model**: Sentence Transformers (`all-MiniLM-L6-v2`)
- **Vector Database**: PostgreSQL + pgvector extension
- **LLM Providers**: Ollama (llama3.2) / OpenAI (gpt-4o-mini)
- **ML Framework**: PyTorch (via Sentence Transformers)

### Backend Stack
- **Web Framework**: Django 5.2 + FastAPI
- **Task Queue**: Celery + RabbitMQ + Redis
- **Database**: PostgreSQL 16 with pgvector
- **API**: Django REST Framework

### DevOps Stack
- **Containerization**: Docker + Docker Compose
- **Monitoring**: Flower (Celery tasks)
- **Deployment**: Production-ready with health checks

---

## Getting Started

See [README.md](README.md) for installation and setup instructions.

## Contributing

This project demonstrates production-ready AI/ML engineering practices. Contributions welcome!

## License

MIT License - See LICENSE file for details.
