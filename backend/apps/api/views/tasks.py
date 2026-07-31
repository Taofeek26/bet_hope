"""
Admin Task Runner API Views

Lets an authenticated admin trigger long-running management commands
(data sync, model training, prediction generation) from the UI and poll
for progress. There is no Celery/Redis broker in this deployment (see
config/settings/production.py), and the web Lambda has a 29s API Gateway
timeout far too short for these jobs, so triggering invokes the sibling
ManageFunction Lambda asynchronously (fire-and-forget) and progress is
tracked via the TaskRun row in Postgres, which lambda_manage_handler.py
updates directly. Polling Postgres (not the Lambda invocation itself)
is what lets the browser tab close and reopen without losing progress.
"""
import json
import logging

import boto3
from django.conf import settings
from rest_framework import status, viewsets, mixins
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from apps.core.models import TaskRun
from apps.api.serializers.tasks import TaskRunSerializer, TaskRunCreateSerializer

logger = logging.getLogger(__name__)


class TaskRunViewSet(mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    """
    POST   /api/v1/admin-tasks/           trigger a new task
    GET    /api/v1/admin-tasks/<id>/      poll a task's status
    GET    /api/v1/admin-tasks/           recent task history
    """
    queryset = TaskRun.objects.all()
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return TaskRunCreateSerializer
        return TaskRunSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()[:20]
        return Response(TaskRunSerializer(qs, many=True).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        command = serializer.validated_data['command']
        args_list = serializer.validated_data.get('args', [])

        if not settings.MANAGE_FUNCTION_NAME:
            return Response(
                {'error': 'MANAGE_FUNCTION_NAME is not configured on this deployment.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        task = TaskRun.objects.create(
            command=command,
            args=args_list,
            triggered_by=getattr(request.user, 'username', ''),
        )

        payload = {
            'command': command,
            'args': args_list,
            'task_id': str(task.id),
        }

        try:
            client = boto3.client('lambda')
            client.invoke(
                FunctionName=settings.MANAGE_FUNCTION_NAME,
                InvocationType='Event',  # async — return immediately, don't wait for it to finish
                Payload=json.dumps(payload).encode('utf-8'),
            )
        except Exception as e:
            logger.exception('Failed to invoke ManageFunction for task %s', task.id)
            task.status = TaskRun.Status.ERROR
            task.error = f'Failed to start: {e}'
            task.save(update_fields=['status', 'error', 'updated_at'])
            return Response(TaskRunSerializer(task).data, status=status.HTTP_502_BAD_GATEWAY)

        return Response(TaskRunSerializer(task).data, status=status.HTTP_202_ACCEPTED)
