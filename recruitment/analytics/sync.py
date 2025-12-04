"""
Analytics Sync Service

Synchronizes data from PostgreSQL (production database) to DuckDB (analytics warehouse).
Implements incremental sync logic to minimize data transfer.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
from django.db.models import Q

from recruitment.models import Application, Candidate, JobPosting
from recruitment.analytics.client import get_client
from recruitment.analytics.schema import initialize_schema

logger = logging.getLogger(__name__)


class AnalyticsSyncService:
    """
    Service for syncing PostgreSQL data to DuckDB analytics warehouse.
    
    Features:
    - Incremental sync (only new/updated records)
    - Full rebuild capability
    - Parquet export
    - Error handling and logging
    """
    
    def __init__(self):
        self.client = get_client()
        # Ensure schema exists
        initialize_schema()
    
    def sync_candidates(self, full_rebuild: bool = False) -> int:
        """
        Sync candidates from PostgreSQL to DuckDB.
        
        Args:
            full_rebuild: If True, replace all data. If False, incremental sync.
            
        Returns:
            Number of candidates synced
        """
        try:
            logger.info(f"🔄 Syncing candidates (full_rebuild={full_rebuild})...")
            
            # Get candidates from PostgreSQL
            if full_rebuild:
                candidates = Candidate.objects.all()
            else:
                # Incremental: only candidates created/updated in last 24 hours
                cutoff = datetime.now() - timedelta(hours=24)
                candidates = Candidate.objects.filter(
                    Q(created_at__gte=cutoff) | Q(embedding_generated_at__gte=cutoff)
                )
            
            if not candidates.exists():
                logger.info("  No candidates to sync")
                return 0
            
            # Convert to DataFrame
            data = []
            for candidate in candidates:
                data.append({
                    'id': candidate.id,
                    'name': candidate.name,
                    'email': candidate.email,
                    'resume_text': candidate.resume_text_cache or '',
                    'created_at': candidate.created_at,
                    'embedding_generated_at': candidate.embedding_generated_at,
                    'has_embedding': candidate.has_embedding
                })
            
            df = pd.DataFrame(data)
            
            # Insert into DuckDB
            mode = 'replace' if full_rebuild else 'append'
            
            if mode == 'append' and self.client.table_exists('dim_candidates'):
                # For incremental, delete existing records first to avoid duplicates
                candidate_ids = df['id'].tolist()
                self.client.execute(
                    f"DELETE FROM dim_candidates WHERE id IN ({','.join(map(str, candidate_ids))})"
                )
            
            self.client.insert_df('dim_candidates', df, mode='append' if not full_rebuild else 'replace')
            
            logger.info(f"✅ Synced {len(df)} candidates to DuckDB")
            return len(df)
            
        except Exception as e:
            logger.error(f"❌ Candidate sync failed: {e}")
            raise
    
    def sync_jobs(self, full_rebuild: bool = False) -> int:
        """
        Sync job postings from PostgreSQL to DuckDB.
        
        Args:
            full_rebuild: If True, replace all data. If False, incremental sync.
            
        Returns:
            Number of jobs synced
        """
        try:
            logger.info(f"🔄 Syncing job postings (full_rebuild={full_rebuild})...")
            
            # Get jobs from PostgreSQL
            if full_rebuild:
                jobs = JobPosting.objects.all()
            else:
                # Incremental: only jobs created/updated in last 24 hours
                cutoff = datetime.now() - timedelta(hours=24)
                jobs = JobPosting.objects.filter(
                    Q(created_at__gte=cutoff) | Q(embedding_generated_at__gte=cutoff)
                )
            
            if not jobs.exists():
                logger.info("  No jobs to sync")
                return 0
            
            # Convert to DataFrame
            data = []
            for job in jobs:
                data.append({
                    'id': job.id,
                    'title': job.title,
                    'description': job.description,
                    'created_at': job.created_at,
                    'embedding_generated_at': job.embedding_generated_at,
                    'has_embedding': job.has_embedding
                })
            
            df = pd.DataFrame(data)
            
            # Insert into DuckDB
            mode = 'replace' if full_rebuild else 'append'
            
            if mode == 'append' and self.client.table_exists('dim_jobs'):
                # For incremental, delete existing records first
                job_ids = df['id'].tolist()
                self.client.execute(
                    f"DELETE FROM dim_jobs WHERE id IN ({','.join(map(str, job_ids))})"
                )
            
            self.client.insert_df('dim_jobs', df, mode='append' if not full_rebuild else 'replace')
            
            logger.info(f"✅ Synced {len(df)} jobs to DuckDB")
            return len(df)
            
        except Exception as e:
            logger.error(f"❌ Job sync failed: {e}")
            raise
    
    def sync_applications(self, full_rebuild: bool = False) -> int:
        """
        Sync applications from PostgreSQL to DuckDB.
        
        This is the main fact table with denormalized data for fast analytics.
        
        Args:
            full_rebuild: If True, replace all data. If False, incremental sync.
            
        Returns:
            Number of applications synced
        """
        try:
            logger.info(f"🔄 Syncing applications (full_rebuild={full_rebuild})...")
            
            # Get applications from PostgreSQL with related data
            if full_rebuild:
                applications = Application.objects.select_related('candidate', 'job').all()
            else:
                # Incremental: only applications created/updated in last 24 hours
                cutoff = datetime.now() - timedelta(hours=24)
                applications = Application.objects.select_related('candidate', 'job').filter(
                    Q(applied_at__gte=cutoff) | Q(updated_at__gte=cutoff)
                )
            
            if not applications.exists():
                logger.info("  No applications to sync")
                return 0
            
            # Convert to DataFrame with denormalized data
            data = []
            for app in applications:
                # Extract AI scores from JSON feedback
                ai_feedback = app.ai_feedback or {}
                detailed_analysis = ai_feedback.get('detailed_analysis', {})
                safety_report = ai_feedback.get('safety_report', {})
                
                # Calculate derived fields
                is_hired = app.status == 'accepted'
                days_to_decision = None
                if app.updated_at and app.applied_at:
                    days_to_decision = (app.updated_at - app.applied_at).days
                
                # Extract safety metrics
                pii_count = len(safety_report.get('pii_entities', []))
                bias_count = len(safety_report.get('bias_issues', []))
                
                # Handle toxicity_score - can be dict or float
                toxicity_data = safety_report.get('toxicity_score', 0.0)
                if isinstance(toxicity_data, dict):
                    # If it's a dict, get the 'toxicity' key or default to 0.0
                    toxicity_score = toxicity_data.get('toxicity', 0.0)
                else:
                    toxicity_score = float(toxicity_data) if toxicity_data else 0.0
                
                has_safety_issues = pii_count > 0 or bias_count > 0 or toxicity_score > 0.7
                
                data.append({
                    'id': app.id,
                    'candidate_id': app.candidate.id,
                    'job_id': app.job.id,
                    'status': app.status,
                    'applied_at': app.applied_at,
                    'updated_at': app.updated_at,
                    'ai_score': app.ai_score,
                    'technical_score': detailed_analysis.get('technical_score'),
                    'experience_score': detailed_analysis.get('experience_score'),
                    'culture_score': detailed_analysis.get('culture_score'),
                    'confidence_score': ai_feedback.get('confidence_score'),
                    'candidate_name': app.candidate.name,
                    'candidate_email': app.candidate.email,
                    'job_title': app.job.title,
                    'job_description': app.job.description,
                    'pii_count': pii_count,
                    'bias_count': bias_count,
                    'toxicity_score': toxicity_score,
                    'has_safety_issues': has_safety_issues,
                    'ai_feedback': str(ai_feedback),  # Convert to JSON string
                    'is_hired': is_hired,
                    'days_to_decision': days_to_decision
                })
            
            df = pd.DataFrame(data)
            
            # Insert into DuckDB
            mode = 'replace' if full_rebuild else 'append'
            
            if mode == 'append' and self.client.table_exists('fact_applications'):
                # For incremental, delete existing records first
                app_ids = df['id'].tolist()
                self.client.execute(
                    f"DELETE FROM fact_applications WHERE id IN ({','.join(map(str, app_ids))})"
                )
            
            self.client.insert_df('fact_applications', df, mode='append' if not full_rebuild else 'replace')
            
            logger.info(f"✅ Synced {len(df)} applications to DuckDB")
            return len(df)
            
        except Exception as e:
            logger.error(f"❌ Application sync failed: {e}")
            raise
    
    def full_sync(self) -> Dict[str, int]:
        """
        Perform a full sync of all data from PostgreSQL to DuckDB.
        
        Returns:
            Dictionary with counts of synced records
        """
        try:
            logger.info("🔄 Starting full analytics warehouse sync...")
            
            results = {
                'candidates': self.sync_candidates(full_rebuild=True),
                'jobs': self.sync_jobs(full_rebuild=True),
                'applications': self.sync_applications(full_rebuild=True)
            }
            
            logger.info(f"✅ Full sync completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Full sync failed: {e}")
            raise
    
    def incremental_sync(self) -> Dict[str, int]:
        """
        Perform an incremental sync (only recent changes).
        
        Returns:
            Dictionary with counts of synced records
        """
        try:
            logger.info("🔄 Starting incremental analytics sync...")
            
            results = {
                'candidates': self.sync_candidates(full_rebuild=False),
                'jobs': self.sync_jobs(full_rebuild=False),
                'applications': self.sync_applications(full_rebuild=False)
            }
            
            logger.info(f"✅ Incremental sync completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Incremental sync failed: {e}")
            raise
    
    def export_to_parquet(self, output_dir: str = 'data/parquet'):
        """
        Export all analytics tables to Parquet files.
        
        Args:
            output_dir: Directory to save Parquet files
        """
        try:
            logger.info(f"📦 Exporting analytics to Parquet: {output_dir}")
            
            tables = ['dim_candidates', 'dim_jobs', 'fact_applications']
            
            for table in tables:
                if self.client.table_exists(table):
                    output_path = f"{output_dir}/{table}.parquet"
                    self.client.export_to_parquet(table, output_path)
            
            logger.info("✅ Parquet export completed")
            
        except Exception as e:
            logger.error(f"❌ Parquet export failed: {e}")
            raise
