"""
Document Models with Vector Embeddings for RAG

Uses pgvector for efficient similarity search on document embeddings.
Supports multiple document types: betting guides, team analyses, strategy docs.
"""
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from pgvector.django import VectorField

from apps.core.models import TimeStampedModel


class DocumentCategory(models.Model):
    """Categories for organizing documents."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'document_categories'
        verbose_name_plural = 'Document Categories'

    def __str__(self):
        return self.name


class Document(TimeStampedModel):
    """
    Document storage for RAG system.

    Stores full documents that are chunked for embedding.
    """

    class DocumentType(models.TextChoices):
        BETTING_GUIDE = 'betting_guide', 'Betting Guide'
        TEAM_ANALYSIS = 'team_analysis', 'Team Analysis'
        STRATEGY = 'strategy', 'Strategy Document'
        MATCH_PREVIEW = 'match_preview', 'Match Preview'
        STATISTICS = 'statistics', 'Statistics Report'
        NEWS = 'news', 'News Article'
        OTHER = 'other', 'Other'

    title = models.CharField(max_length=500)
    content = models.TextField()
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.OTHER
    )
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents'
    )

    # Source information
    source_url = models.URLField(blank=True, null=True)
    author = models.CharField(max_length=200, blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    # Related entities
    teams = models.ManyToManyField(
        'teams.Team',
        related_name='documents',
        blank=True
    )
    leagues = models.ManyToManyField(
        'leagues.League',
        related_name='documents',
        blank=True
    )

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.title


class DocumentChunk(TimeStampedModel):
    """
    Document chunks with vector embeddings.

    Documents are split into chunks for more accurate retrieval.
    Each chunk has its own embedding vector.
    """

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks'
    )

    # Chunk content
    content = models.TextField()
    chunk_index = models.PositiveIntegerField()

    # Vector embedding (1536 dimensions for OpenAI, adjustable)
    embedding = VectorField(dimensions=1536, null=True, blank=True)

    # Metadata
    token_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'document_chunks'
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']

    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"


class AIRecommendation(TimeStampedModel):
    """
    Stores AI-generated recommendations based on predictions.

    Links predictions with AI analysis using RAG context.
    """

    class Provider(models.TextChoices):
        OPENAI = 'openai', 'OpenAI (GPT)'
        ANTHROPIC = 'anthropic', 'Anthropic (Claude)'
        GOOGLE = 'google', 'Google (Gemini)'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    # Link to prediction
    prediction = models.ForeignKey(
        'predictions.Prediction',
        on_delete=models.CASCADE,
        related_name='ai_recommendations'
    )

    # AI provider used
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.OPENAI
    )
    model_name = models.CharField(max_length=100)

    # Request/Response
    prompt = models.TextField()
    response = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # RAG context
    context_chunks = models.ManyToManyField(
        DocumentChunk,
        related_name='recommendations',
        blank=True
    )
    context_summary = models.TextField(blank=True)

    # Analysis results
    recommendation = models.TextField(blank=True)
    confidence_assessment = models.TextField(blank=True)
    risk_analysis = models.TextField(blank=True)
    key_factors = models.JSONField(default=list, blank=True)

    # Metadata
    tokens_used = models.PositiveIntegerField(default=0)
    processing_time_ms = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'ai_recommendations'
        ordering = ['-created_at']

    def __str__(self):
        return f"AI Recommendation for Prediction {self.prediction_id}"


class EmbeddingCache(models.Model):
    """
    Cache for text embeddings to reduce API calls.
    """

    text_hash = models.CharField(max_length=64, unique=True, db_index=True)
    embedding = VectorField(dimensions=1536)
    model = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'embedding_cache'

    def __str__(self):
        return f"Embedding {self.text_hash[:16]}..."
