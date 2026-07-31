"""
Task Run Serializers

Serializers for the admin task-runner (sync/train/predict triggered from
the UI and polled for progress).
"""
from rest_framework import serializers

from apps.core.models import TaskRun


class TaskRunSerializer(serializers.ModelSerializer):
    command_display = serializers.CharField(source='get_command_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = TaskRun
        fields = [
            'id', 'command', 'command_display', 'args', 'status', 'status_display',
            'triggered_by', 'created_at', 'started_at', 'finished_at',
            'duration_seconds', 'log_tail', 'error',
        ]
        read_only_fields = fields

    def get_duration_seconds(self, obj):
        if not obj.started_at:
            return None
        end = obj.finished_at or None
        from django.utils import timezone
        end = end or timezone.now()
        return round((end - obj.started_at).total_seconds(), 1)


class TaskRunCreateSerializer(serializers.Serializer):
    # Deliberately not ModelSerializer for `command`/`args` — this is the
    # one input surface that ends up as an argv list passed to
    # manage.py inside a Lambda invocation, so the choice of allowed
    # commands and coarse arg validation below is a security boundary,
    # not just a shape check.
    command = serializers.ChoiceField(choices=TaskRun.Command.choices)
    args = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)

    ALLOWED_ARGS = {
        TaskRun.Command.SYNC_DATA: {
            '--fixtures', '--fixtures-only', '--recent-only', '--clear',
            '--leagues', '--seasons',
        },
        TaskRun.Command.TRAIN_MODEL: {
            '--leagues', '--seasons', '--tune',
        },
        TaskRun.Command.GENERATE_PREDICTIONS: {
            '--upcoming', '--historical', '--validate', '--clear',
            '--days', '--seasons',
        },
    }

    def validate(self, attrs):
        command = attrs['command']
        allowed_flags = self.ALLOWED_ARGS.get(command, set())
        for token in attrs.get('args', []):
            flag = token if token.startswith('--') else None
            if flag and flag not in allowed_flags:
                raise serializers.ValidationError(f'Argument "{token}" is not allowed for {command}')
        return attrs
