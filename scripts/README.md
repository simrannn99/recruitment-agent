# 🛠️ Scripts Directory

Utility scripts for development, testing, and deployment.

## 📁 Contents

### **Development Scripts**

#### `start_services.py`
Starts both FastAPI and Django services together.

**Usage:**
```bash
.\venv\Scripts\python .\scripts\start_services.py
```

**What it does:**
- Starts FastAPI on port 8000
- Starts Django on port 8001
- Handles graceful shutdown with Ctrl+C

---

### **Configuration Scripts**

#### `switch_provider.py`
Switch between Ollama and OpenAI LLM providers.

**Usage:**
```bash
# Switch to Ollama
.\venv\Scripts\python .\scripts\switch_provider.py ollama

# Switch to OpenAI
.\venv\Scripts\python .\scripts\switch_provider.py openai
```

**What it does:**
- Updates `.env` file with selected provider
- Validates configuration
- Shows current settings

---

### **Test Scripts**

#### `test_api.py`
Test the FastAPI AI analysis service.

**Usage:**
```bash
.\venv\Scripts\python .\scripts\test_api.py
```

**Tests:**
- FastAPI health check
- AI analysis endpoint
- Resume screening functionality

---

#### `test_django_backend.py`
Test Django backend functionality.

**Usage:**
```bash
.\venv\Scripts\python .\scripts\test_django_backend.py
```

**Tests:**
- Database connectivity
- Model creation
- AI integration
- Signal handlers

---

#### `test_ollama.py`
Test Ollama connection and functionality.

**Usage:**
```bash
.\venv\Scripts\python .\scripts\test_ollama.py
```

**Tests:**
- Ollama service availability
- Model availability
- LangChain integration

---

#### `test_pdf_extraction.py`
Test PDF text extraction functionality.

**Usage:**
```bash
.\venv\Scripts\python .\scripts\test_pdf_extraction.py
```

**Tests:**
- PDF parsing
- Text extraction
- Metadata extraction
- Error handling

---

## 🚀 Quick Start

### Start Development Services
```bash
.\venv\Scripts\python .\scripts\start_services.py
```

### Run All Tests
```bash
# Test FastAPI
.\venv\Scripts\python .\scripts\test_api.py

# Test Django
.\venv\Scripts\python .\scripts\test_django_backend.py

# Test Ollama
.\venv\Scripts\python .\scripts\test_ollama.py

# Test PDF extraction
.\venv\Scripts\python .\scripts\test_pdf_extraction.py
```

### Switch LLM Provider
```bash
# Use Ollama (local)
.\venv\Scripts\python .\scripts\switch_provider.py ollama

# Use OpenAI (cloud)
.\venv\Scripts\python .\scripts\switch_provider.py openai
```

---

## 📝 Notes

- All scripts should be run from the project root directory
- Make sure virtual environment is activated
- Ensure required services (Ollama, PostgreSQL) are running before testing

