"""
Core Models - Base classes for all models
"""
import uuid
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


class TaskRun(TimeStampedModel):
    """
    Tracks a single invocation of a background management command (data
    sync, model training, prediction generation) triggered from the UI.

    Written to by two different processes: the API view creates the row
    and invokes ManageFunction asynchronously; the Lambda handler running
    the actual command (lambda_manage_handler.py) updates status/output as
    it runs. Polling this row from the frontend is what lets the UI show
    live progress without a websocket or a Celery/Redis broker, and lets
    it survive the browser tab closing since the state lives in Postgres,
    not in the client.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        ERROR = 'error', 'Error'
        TIMEOUT = 'timeout', 'Timeout'

    class Command(models.TextChoices):
        SYNC_DATA = 'sync_real_data', 'Sync Data'
        TRAIN_MODEL = 'train_model', 'Train Model'
        GENERATE_PREDICTIONS = 'generate_predictions', 'Generate Predictions'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    command = models.CharField(max_length=40, choices=Command.choices)
    args = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    triggered_by = models.CharField(max_length=150, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    log_tail = models.TextField(blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.command} [{self.status}] {self.id}'
