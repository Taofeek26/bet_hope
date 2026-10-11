from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Write AI previews for the biggest matches in the next 48 hours'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=8)

    def handle(self, *args, **options):
        from apps.engage.previews import generate_previews
        self.stdout.write(f"AI match previews written: {generate_previews(limit=options['limit'])}")
