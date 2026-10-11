from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Send a test push alert to every subscribed device (or the newest one with --latest)'

    def add_arguments(self, parser):
        parser.add_argument('--latest', action='store_true', help='Only the most recently subscribed device')

    def handle(self, *args, **options):
        from apps.engage.models import PushSubscription
        from apps.engage.push import _send, SITE
        subs = PushSubscription.objects.order_by('-created_at')
        subs = list(subs[:1]) if options['latest'] else list(subs)
        ok = sum(_send(s, {'title': 'Bet Hope test alert', 'body': 'Push alerts are working on this device.',
                           'url': f'{SITE}/', 'tag': 'test'}) for s in subs)
        self.stdout.write(f'Sent {ok} of {len(subs)}')
