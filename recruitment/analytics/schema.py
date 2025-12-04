"""
DuckDB Analytics Warehouse Schema

Defines the schema for the analytics warehouse with fact and dimension tables
optimized for analytical queries.
"""

import logging
from recruitment.analytics.client import get_client

logger = logging.getLogger(__name__)


# SQL schema definitions
SCHEMA_SQL = """
-- ============================================================================
-- DIMENSION TABLES
-- ============================================================================

-- Candidates dimension table
CREATE TABLE IF NOT EXISTS dim_candidates (
    id INTEGER PRIMARY KEY,
    name VARCHAR,
    email VARCHAR,
    resume_text TEXT,
    created_at TIMESTAMP,
    embedding_generated_at TIMESTAMP,
    has_embedding BOOLEAN
);

-- Job postings dimension table
CREATE TABLE IF NOT EXISTS dim_jobs (
    id INTEGER PRIMARY KEY,
    title VARCHAR,
    description TEXT,
    created_at TIMESTAMP,
    embedding_generated_at TIMESTAMP,
    has_embedding BOOLEAN
);

-- ============================================================================
-- FACT TABLES
-- ============================================================================

-- Applications fact table (denormalized for fast queries)
CREATE TABLE IF NOT EXISTS fact_applications (
    -- Primary keys
    id INTEGER PRIMARY KEY,
    candidate_id INTEGER,
    job_id INTEGER,
    
    -- Application details
    status VARCHAR,
    applied_at TIMESTAMP,
    updated_at TIMESTAMP,
    
    -- AI scores
    ai_score INTEGER,
    technical_score INTEGER,
    experience_score INTEGER,
    culture_score INTEGER,
    confidence_score DOUBLE,
    
    -- Denormalized candidate info
    candidate_name VARCHAR,
    candidate_email VARCHAR,
    
    -- Denormalized job info
    job_title VARCHAR,
    job_description TEXT,
    
    -- Safety metrics
    pii_count INTEGER DEFAULT 0,
    bias_count INTEGER DEFAULT 0,
    toxicity_score DOUBLE DEFAULT 0.0,
    has_safety_issues BOOLEAN DEFAULT FALSE,
    
    -- AI feedback (JSON)
    ai_feedback JSON,
    
    -- Derived fields
    is_hired BOOLEAN,
    days_to_decision INTEGER
);

-- Create indexes separately (DuckDB syntax)
CREATE INDEX IF NOT EXISTS idx_applied_at ON fact_applications(applied_at);
CREATE INDEX IF NOT EXISTS idx_status ON fact_applications(status);
CREATE INDEX IF NOT EXISTS idx_ai_score ON fact_applications(ai_score);
CREATE INDEX IF NOT EXISTS idx_candidate_id ON fact_applications(candidate_id);
CREATE INDEX IF NOT EXISTS idx_job_id ON fact_applications(job_id);

-- ============================================================================
-- ANALYTICS VIEWS
-- ============================================================================

-- Hiring funnel view
CREATE OR REPLACE VIEW v_hiring_funnel AS
SELECT 
    status,
    COUNT(*) as count,
    AVG(ai_score) as avg_ai_score,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM fact_applications
WHERE ai_score IS NOT NULL
GROUP BY status
ORDER BY 
    CASE status 
        WHEN 'pending' THEN 1 
        WHEN 'accepted' THEN 2 
        WHEN 'rejected' THEN 3 
    END;

-- AI performance over time
CREATE OR REPLACE VIEW v_ai_performance AS
SELECT 
    DATE_TRUNC('day', applied_at) as date,
    COUNT(*) as applications,
    AVG(ai_score) as avg_ai_score,
    AVG(technical_score) as avg_technical,
    AVG(experience_score) as avg_experience,
    AVG(culture_score) as avg_culture,
    AVG(confidence_score) as avg_confidence,
    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted_count,
    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count
FROM fact_applications
WHERE ai_score IS NOT NULL
GROUP BY date
ORDER BY date DESC;

-- Top candidates view
CREATE OR REPLACE VIEW v_top_candidates AS
SELECT 
    candidate_id,
    candidate_name,
    candidate_email,
    COUNT(*) as total_applications,
    AVG(ai_score) as avg_ai_score,
    MAX(ai_score) as max_ai_score,
    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted_count,
    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count
FROM fact_applications
WHERE ai_score IS NOT NULL
GROUP BY candidate_id, candidate_name, candidate_email
HAVING COUNT(*) >= 1
ORDER BY avg_ai_score DESC;

-- Safety compliance view
CREATE OR REPLACE VIEW v_safety_compliance AS
SELECT 
    DATE_TRUNC('week', applied_at) as week,
    COUNT(*) as total_applications,
    SUM(pii_count) as total_pii_detected,
    SUM(bias_count) as total_bias_detected,
    AVG(toxicity_score) as avg_toxicity,
    SUM(CASE WHEN has_safety_issues THEN 1 ELSE 0 END) as applications_with_issues,
    SUM(CASE WHEN has_safety_issues THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as issue_percentage
FROM fact_applications
GROUP BY week
ORDER BY week DESC;

-- Job performance view
CREATE OR REPLACE VIEW v_job_performance AS
SELECT 
    job_id,
    job_title,
    COUNT(*) as total_applications,
    AVG(ai_score) as avg_ai_score,
    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as accepted_count,
    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
    AVG(days_to_decision) as avg_days_to_decision
FROM fact_applications
WHERE ai_score IS NOT NULL
GROUP BY job_id, job_title
HAVING COUNT(*) >= 1
ORDER BY total_applications DESC;
"""


def initialize_schema():
    """
    Initialize the DuckDB analytics warehouse schema.
    
    Creates all dimension tables, fact tables, and analytical views.
    """
    try:
        client = get_client()
        
        logger.info("🔨 Initializing DuckDB analytics warehouse schema...")
        
        # Execute schema creation SQL
        client.execute(SCHEMA_SQL)
        
        logger.info("✅ DuckDB schema initialized successfully")
        
        # Log table info
        tables = ['dim_candidates', 'dim_jobs', 'fact_applications']
        for table in tables:
            if client.table_exists(table):
                info = client.get_table_info(table)
                logger.info(f"  📊 {table}: {info['row_count']} rows")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Schema initialization failed: {e}")
        raise


def drop_all_tables():
    """Drop all tables and views (for testing/reset)."""
    try:
        client = get_client()
        
        logger.warning("⚠️  Dropping all analytics tables and views...")
        
        # Drop views
        views = ['v_hiring_funnel', 'v_ai_performance', 'v_top_candidates', 
                'v_safety_compliance', 'v_job_performance']
        for view in views:
            client.execute(f"DROP VIEW IF EXISTS {view}")
        
        # Drop tables
        tables = ['fact_applications', 'dim_candidates', 'dim_jobs']
        for table in tables:
            client.execute(f"DROP TABLE IF EXISTS {table}")
        
        logger.info("✅ All tables and views dropped")
        
    except Exception as e:
        logger.error(f"❌ Drop tables failed: {e}")
        raise


def get_schema_info():
    """Get information about all tables and views in the warehouse."""
    try:
        client = get_client()
        
        # Get all tables
        tables_df = client.query_df("""
            SELECT 
                table_name,
                table_type
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_type, table_name
        """)
        
        info = {
            'tables': [],
            'views': []
        }
        
        for _, row in tables_df.iterrows():
            table_name = row['table_name']
            table_type = row['table_type']
            
            if table_type == 'BASE TABLE':
                table_info = client.get_table_info(table_name)
                info['tables'].append(table_info)
            else:
                info['views'].append({'name': table_name})
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to get schema info: {e}")
        return {'tables': [], 'views': []}
