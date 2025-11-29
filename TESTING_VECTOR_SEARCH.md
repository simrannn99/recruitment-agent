# Vector Search Testing Guide

Quick guide to test the vector search implementation.

## Prerequisites

Ensure these services are running:
```bash
# Check if services are running
# - PostgreSQL (port 5432)
# - RabbitMQ (port 5672)
# - Redis (port 6379)
# - Django (port 8001)
# - Celery worker
```

## Step-by-Step Testing

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `pgvector>=0.2.5`
- `sentence-transformers>=2.2.0`
- `numpy>=1.24.0`

### Step 2: Run Database Migration

```bash
python manage.py migrate
```

Expected output:
```
Running migrations:
  Applying recruitment.0002_add_vector_embeddings... OK
```

### Step 3: Check Database Status

```bash
python manage.py generate_embeddings --stats
```

Expected output:
```
=== Embedding Statistics ===

Candidates:
  Total: X
  With embeddings: Y (Z%)
  Without embeddings: N

Job Postings:
  Total: X
  With embeddings: Y (Z%)
  Without embeddings: N
```

### Step 4: Generate Embeddings (if needed)

```bash
# Generate for all existing data
python manage.py generate_embeddings --all
```

Monitor progress in Flower: http://localhost:5555

### Step 5: Run Automated Tests

```bash
python scripts/test_vector_search.py
```

This tests:
1. ✓ Embedding service initialization
2. ✓ Database status
3. ✓ Embedding generation tasks
4. ✓ API endpoints
5. ✓ Query text search
6. ✓ Similar candidates search

### Step 6: Manual API Testing

#### Test 1: Find Candidates for a Job

```bash
curl -X POST http://localhost:8001/api/search/candidates/ \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 1,
    "limit": 5,
    "similarity_threshold": 0.7
  }'
```

#### Test 2: Search with Custom Query

```bash
curl -X POST http://localhost:8001/api/search/candidates/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "Python developer with Django experience",
    "limit": 10
  }'
```

#### Test 3: Find Similar Candidates

```bash
curl -X POST http://localhost:8001/api/search/similar-candidates/ \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_id": 1,
    "limit": 5
  }'
```

### Step 7: Test Django Admin

1. Navigate to: http://localhost:8001/admin/
2. Go to **Job Postings**
3. Select a job posting
4. Choose action: **"Find matching candidates for job"**
5. View results in admin message

## Troubleshooting

### Issue: Migration fails with "pgvector extension not found"

**Solution**: Install pgvector for PostgreSQL
```bash
# Windows (using PostgreSQL installer)
# Download from: https://github.com/pgvector/pgvector/releases

# Or use Docker with pgvector pre-installed
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password ankane/pgvector
```

### Issue: "No module named 'sentence_transformers'"

**Solution**: Install dependencies
```bash
pip install sentence-transformers
```

### Issue: Embedding generation stuck

**Solution**: Check Celery worker is running
```bash
celery -A recruitment_backend worker -l info --pool=solo
```

### Issue: API returns 404

**Solution**: Ensure Django server is running on port 8001
```bash
python manage.py runserver 8001
```

### Issue: No results from search

**Possible causes:**
1. No embeddings generated yet
2. Similarity threshold too high (try 0.5 or lower)
3. No candidates/jobs in database

**Solution:**
```bash
# Check status
python manage.py generate_embeddings --stats

# Generate embeddings
python manage.py generate_embeddings --all

# Lower similarity threshold in API call
```

## Quick Test Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Migration run (`python manage.py migrate`)
- [ ] Embeddings generated (`python manage.py generate_embeddings --all`)
- [ ] Celery worker running
- [ ] Django server running (port 8001)
- [ ] Test script passes (`python scripts/test_vector_search.py`)
- [ ] API endpoints working (curl tests)
- [ ] Admin actions working

## Next Steps

Once testing is complete:

1. **Monitor Performance**: Check Flower dashboard for task execution times
2. **Adjust Thresholds**: Fine-tune similarity thresholds based on results
3. **Add More Data**: Test with larger datasets
4. **Production Deployment**: Update docker-compose.yml if needed
