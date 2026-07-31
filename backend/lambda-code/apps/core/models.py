"""
Core Models - Base classes for all models
"""
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model with created/updated timestamps.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SyncedModel(TimeStampedModel):
    """
    Abstract model for data synced from external sources.
    """
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_source = models.CharField(max_length=50, blank=True)

    class Meta:
        abstract = True

    def mark_synced(self, source: str = ''):
        """Mark this record as synced."""
        self.last_synced_at = timezone.now()
        if source:
            self.sync_source = source
        self.save(update_fields=['last_synced_at', 'sync_source', 'updated_at'])
