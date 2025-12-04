"""
Celery Tasks for Analytics Warehouse Synchronization

Automated tasks for syncing PostgreSQL data to DuckDB analytics warehouse.
"""

import logging
from celery import shared_task
from recruitment.analytics.sync import AnalyticsSyncService

logger = logging.getLogger(__name__)


@shared_task(
    name='analytics.incremental_sync',
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def incremental_sync_task(self):
    """
    Incremental sync task - runs every 15 minutes.
    
    Syncs only records created/updated in the last 24 hours.
    """
    try:
        logger.info("🔄 Starting incremental analytics sync task...")
        
        service = AnalyticsSyncService()
        results = service.incremental_sync()
        
        logger.info(f"✅ Incremental sync completed: {results}")
        return {
            'status': 'success',
            'results': results
        }
        
    except Exception as e:
        logger.error(f"❌ Incremental sync task failed: {e}")
        # Retry the task
        raise self.retry(exc=e)


@shared_task(
    name='analytics.full_sync',
    bind=True,
    max_retries=2,
    default_retry_delay=600  # 10 minutes
)
def full_sync_task(self):
    """
    Full sync task - runs daily at 2 AM.
    
    Rebuilds the entire analytics warehouse from scratch.
    """
    try:
        logger.info("🔄 Starting full analytics sync task...")
        
        service = AnalyticsSyncService()
        results = service.full_sync()
        
        logger.info(f"✅ Full sync completed: {results}")
        return {
            'status': 'success',
            'results': results
        }
        
    except Exception as e:
        logger.error(f"❌ Full sync task failed: {e}")
        # Retry the task
        raise self.retry(exc=e)


@shared_task(
    name='analytics.export_parquet',
    bind=True
)
def export_parquet_task(self, output_dir: str = 'data/parquet'):
    """
    Export analytics tables to Parquet files.
    
    Args:
        output_dir: Directory to save Parquet files
    """
    try:
        logger.info(f"📦 Starting Parquet export task: {output_dir}")
        
        service = AnalyticsSyncService()
        service.export_to_parquet(output_dir)
        
        logger.info("✅ Parquet export completed")
        return {
            'status': 'success',
            'output_dir': output_dir
        }
        
    except Exception as e:
        logger.error(f"❌ Parquet export task failed: {e}")
        raise


@shared_task(
    name='analytics.train_models',
    bind=True,
    max_retries=2,
    default_retry_delay=600  # 10 minutes
)
def train_models_task(self):
    """
    Train ML models on analytics data.
    
    Runs weekly on Sunday at 3 AM to retrain models with latest data.
    """
    try:
        logger.info("🤖 Starting ML model training task...")
        
        from recruitment.analytics.ml_models import train_all_models
        
        results = train_all_models()
        
        logger.info(f"✅ ML model training completed: {results}")
        return {
            'status': 'success',
            'results': results
        }
        
    except Exception as e:
        logger.error(f"❌ ML model training task failed: {e}")
        # Retry the task
        raise self.retry(exc=e)


@shared_task(
    name='analytics.sync_on_application_update',
    bind=True
)
def sync_on_application_update(self, application_id: int):
    """
    Triggered when an application is created or updated.
    
    Syncs the specific application to DuckDB immediately.
    
    Args:
        application_id: ID of the application to sync
    """
    try:
        from recruitment.models import Application
        
        logger.info(f"🔄 Syncing application {application_id} to analytics...")
        
        # Get the application
        app = Application.objects.select_related('candidate', 'job').get(id=application_id)
        
        # Sync to DuckDB
        service = AnalyticsSyncService()
        
        # For now, just trigger incremental sync
        # In production, you could optimize to sync just this one record
        results = service.incremental_sync()
        
        logger.info(f"✅ Application {application_id} synced to analytics")
        return {
            'status': 'success',
            'application_id': application_id
        }
        
    except Exception as e:
        logger.error(f"❌ Application sync failed: {e}")
        raise
