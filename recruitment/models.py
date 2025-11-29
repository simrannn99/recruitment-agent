from django.db import models
from django.core.validators import EmailValidator
from pgvector.django import VectorField


class JobPosting(models.Model):
    """Model to store job postings."""
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Vector search fields
    description_embedding = VectorField(dimensions=384, null=True, blank=True)
    embedding_generated_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def has_embedding(self):
        """Check if job posting has an embedding."""
        return self.description_embedding is not None


class Candidate(models.Model):
    """Model to store candidate information."""
    name = models.CharField(max_length=255)
    email = models.EmailField(validators=[EmailValidator()])
    resume_file = models.FileField(upload_to='resumes/')
    
    # Vector search fields
    resume_text_cache = models.TextField(null=True, blank=True, help_text="Cached extracted resume text")
    resume_embedding = VectorField(dimensions=384, null=True, blank=True)
    embedding_generated_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    @property
    def has_embedding(self):
        """Check if candidate has an embedding."""
        return self.resume_embedding is not None


class Application(models.Model):
    """Model to store job applications and AI analysis results."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    job = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    ai_score = models.IntegerField(null=True, blank=True)
    ai_feedback = models.JSONField(null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-applied_at']
        unique_together = ['candidate', 'job']
    
    def __str__(self):
        return f"{self.candidate.name} -> {self.job.title} ({self.status})"
