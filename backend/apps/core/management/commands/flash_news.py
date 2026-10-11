from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Scan BBC / Sky / ESPN headlines for clubs with a fixture in the next 7 days (flash feed)'

    def handle(self, *args, **options):
        from apps.engage.flash import scrape_team_news
        r = scrape_team_news()
        self.stdout.write(f"Team news: {r['matched']} headlines about upcoming teams, {r['created']} new")
