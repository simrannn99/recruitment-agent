"""
Django management command to generate embeddings for candidates and jobs.

Usage:
    python manage.py generate_embeddings --model candidate
    python manage.py generate_embeddings --model job
    python manage.py generate_embeddings --all
    python manage.py generate_embeddings --stats
"""
from django.core.management.base import BaseCommand
from recruitment.models import Candidate, JobPosting
from recruitment.tasks import backfill_embeddings


class Command(BaseCommand):
    help = 'Generate embeddings for candidates and/or job postings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            choices=['candidate', 'job', 'all'],
            default='all',
            help='Which model to generate embeddings for (default: all)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate embeddings even if they already exist'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show embedding statistics without generating'
        )

    def handle(self, *args, **options):
        model_type = options['model']
        force = options['force']
        show_stats = options['stats']

        if show_stats:
            self._show_statistics()
            return

        self.stdout.write(self.style.SUCCESS(f'\nStarting embedding generation for: {model_type}'))
        self.stdout.write(f'Force regenerate: {force}\n')

        # Queue backfill task
        result = backfill_embeddings.delay(model_type=model_type, force=force)
        
        self.stdout.write(self.style.SUCCESS(
            f'\nEmbedding generation task queued (Task ID: {result.id})'
        ))
        self.stdout.write('Check Flower dashboard for progress: http://localhost:5555\n')

    def _show_statistics(self):
        """Display embedding statistics."""
        self.stdout.write(self.style.SUCCESS('\n=== Embedding Statistics ===\n'))

        # Candidate statistics
        total_candidates = Candidate.objects.count()
        candidates_with_embeddings = Candidate.objects.filter(
            resume_embedding__isnull=False
        ).count()
        candidates_without = total_candidates - candidates_with_embeddings

        self.stdout.write(f'Candidates:')
        self.stdout.write(f'  Total: {total_candidates}')
        self.stdout.write(self.style.SUCCESS(
            f'  With embeddings: {candidates_with_embeddings} '
            f'({candidates_with_embeddings/total_candidates*100 if total_candidates > 0 else 0:.1f}%)'
        ))
        if candidates_without > 0:
            self.stdout.write(self.style.WARNING(
                f'  Without embeddings: {candidates_without}'
            ))
        self.stdout.write('')

        # Job statistics
        total_jobs = JobPosting.objects.count()
        jobs_with_embeddings = JobPosting.objects.filter(
            description_embedding__isnull=False
        ).count()
        jobs_without = total_jobs - jobs_with_embeddings

        self.stdout.write(f'Job Postings:')
        self.stdout.write(f'  Total: {total_jobs}')
        self.stdout.write(self.style.SUCCESS(
            f'  With embeddings: {jobs_with_embeddings} '
            f'({jobs_with_embeddings/total_jobs*100 if total_jobs > 0 else 0:.1f}%)'
        ))
        if jobs_without > 0:
            self.stdout.write(self.style.WARNING(
                f'  Without embeddings: {jobs_without}'
            ))
        self.stdout.write('')
