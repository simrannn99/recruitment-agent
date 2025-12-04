"""
Django management command to initialize and manage the analytics warehouse.

Usage:
    python manage.py analytics init          # Initialize schema
    python manage.py analytics sync          # Full sync
    python manage.py analytics sync --incremental  # Incremental sync
    python manage.py analytics train         # Train ML models
    python manage.py analytics export        # Export to Parquet
"""

from django.core.management.base import BaseCommand
from recruitment.analytics.schema import initialize_schema, get_schema_info
from recruitment.analytics.sync import AnalyticsSyncService
from recruitment.analytics.ml_models import train_all_models
from recruitment.analytics.queries import get_analytics_summary
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manage the DuckDB analytics warehouse'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['init', 'sync', 'train', 'export', 'info'],
            help='Action to perform'
        )
        parser.add_argument(
            '--incremental',
            action='store_true',
            help='Perform incremental sync instead of full sync'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='data/parquet',
            help='Output directory for Parquet export'
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'init':
            self.init_schema()
        elif action == 'sync':
            self.sync_data(incremental=options['incremental'])
        elif action == 'train':
            self.train_models()
        elif action == 'export':
            self.export_parquet(output_dir=options['output_dir'])
        elif action == 'info':
            self.show_info()

    def init_schema(self):
        """Initialize the analytics warehouse schema."""
        self.stdout.write(self.style.WARNING('🔨 Initializing analytics warehouse schema...'))
        
        try:
            initialize_schema()
            self.stdout.write(self.style.SUCCESS('✅ Schema initialized successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Schema initialization failed: {e}'))

    def sync_data(self, incremental=False):
        """Sync data from PostgreSQL to DuckDB."""
        sync_type = 'incremental' if incremental else 'full'
        self.stdout.write(self.style.WARNING(f'🔄 Starting {sync_type} sync...'))
        
        try:
            service = AnalyticsSyncService()
            
            if incremental:
                results = service.incremental_sync()
            else:
                results = service.full_sync()
            
            self.stdout.write(self.style.SUCCESS(f'✅ Sync completed:'))
            self.stdout.write(f'  • Candidates: {results["candidates"]}')
            self.stdout.write(f'  • Jobs: {results["jobs"]}')
            self.stdout.write(f'  • Applications: {results["applications"]}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Sync failed: {e}'))

    def train_models(self):
        """Train ML models."""
        self.stdout.write(self.style.WARNING('🤖 Training ML models...'))
        
        try:
            results = train_all_models()
            
            self.stdout.write(self.style.SUCCESS('✅ Model training completed:'))
            
            if 'candidate_success' in results and 'error' not in results['candidate_success']:
                metrics = results['candidate_success']
                self.stdout.write(f'\n  📊 Candidate Success Predictor:')
                self.stdout.write(f'    • Accuracy: {metrics["accuracy"]:.3f}')
                self.stdout.write(f'    • Precision: {metrics["precision"]:.3f}')
                self.stdout.write(f'    • Recall: {metrics["recall"]:.3f}')
                self.stdout.write(f'    • F1 Score: {metrics["f1_score"]:.3f}')
            
            if 'time_to_hire' in results and 'error' not in results['time_to_hire']:
                metrics = results['time_to_hire']
                self.stdout.write(f'\n  ⏱️  Time-to-Hire Predictor:')
                self.stdout.write(f'    • MAE: {metrics["mae"]:.1f} days')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Model training failed: {e}'))

    def export_parquet(self, output_dir):
        """Export analytics to Parquet files."""
        self.stdout.write(self.style.WARNING(f'📦 Exporting to Parquet: {output_dir}'))
        
        try:
            service = AnalyticsSyncService()
            service.export_to_parquet(output_dir)
            
            self.stdout.write(self.style.SUCCESS(f'✅ Export completed to {output_dir}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Export failed: {e}'))

    def show_info(self):
        """Show analytics warehouse information."""
        self.stdout.write(self.style.WARNING('📊 Analytics Warehouse Information'))
        
        try:
            # Get schema info
            info = get_schema_info()
            
            self.stdout.write(self.style.SUCCESS('\n📋 Tables:'))
            for table in info['tables']:
                self.stdout.write(f'  • {table["table_name"]}: {table["row_count"]} rows')
            
            self.stdout.write(self.style.SUCCESS('\n👁️  Views:'))
            for view in info['views']:
                self.stdout.write(f'  • {view["name"]}')
            
            # Get analytics summary
            summary = get_analytics_summary()
            
            if summary:
                self.stdout.write(self.style.SUCCESS('\n📈 Analytics Summary:'))
                self.stdout.write(f'  • Total Applications: {summary.get("total_applications", 0)}')
                self.stdout.write(f'  • Unique Candidates: {summary.get("unique_candidates", 0)}')
                self.stdout.write(f'  • Unique Jobs: {summary.get("unique_jobs", 0)}')
                self.stdout.write(f'  • Average AI Score: {summary.get("avg_ai_score", 0):.1f}')
                self.stdout.write(f'  • Acceptance Rate: {summary.get("acceptance_rate", 0):.1%}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to get info: {e}'))
