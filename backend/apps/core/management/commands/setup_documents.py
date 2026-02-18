"""
Setup Documents Management Command

Initializes the document database with strategy guides and runs initial embedding.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Setup initial documents for RAG system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--embed',
            action='store_true',
            help='Also embed documents after creating them',
        )
        parser.add_argument(
            '--async',
            action='store_true',
            dest='run_async',
            help='Run as Celery tasks instead of synchronously',
        )

    def handle(self, *args, **options):
        self.stdout.write('Setting up documents for RAG system...\n')

        if options['run_async']:
            self._run_async()
        else:
            self._run_sync(options['embed'])

    def _run_async(self):
        """Run document setup as Celery tasks."""
        from tasks.documents import refresh_all_documents

        self.stdout.write('Queueing document refresh tasks...')
        result = refresh_all_documents.delay()
        self.stdout.write(self.style.SUCCESS(
            f'Document refresh queued. Task ID: {result.id}'
        ))

    def _run_sync(self, embed=False):
        """Run document setup synchronously."""
        from apps.documents.models import Document, DocumentCategory

        # Strategy content
        strategies = [
            {
                'title': 'Understanding Home Advantage',
                'content': '''
Home advantage in football is a well-documented phenomenon. Teams playing at their home stadium
typically win more often than when playing away. Key factors include:

1. **Crowd Support**: Home fans create an atmosphere that can boost player confidence and
   potentially influence referee decisions.

2. **Familiarity**: Players know the pitch dimensions, surface conditions, and stadium layout.

3. **Travel Fatigue**: Away teams often travel, which can affect performance.

4. **Statistical Evidence**: Historically, home teams win approximately 45-50% of matches,
   with away wins at 25-30% and draws at 25-30%.

When analyzing predictions, a home win probability significantly above 50% suggests strong
home advantage factors are at play.
''',
                'document_type': 'betting_guide',
            },
            {
                'title': 'Over/Under 2.5 Goals Analysis',
                'content': '''
The Over/Under 2.5 goals market is one of the most popular betting markets. Analysis factors:

**Factors favoring Over 2.5:**
- High-scoring teams with strong attacks
- Weak defensive records
- Historical head-to-head high-scoring matches
- Open, attacking playing styles
- Important matches where teams need wins

**Factors favoring Under 2.5:**
- Defensive teams with low goals conceded
- Teams in poor scoring form
- Tactical, cautious matches (e.g., cup ties)
- Weather conditions affecting play
- Historical low-scoring fixtures

**Statistical Benchmarks:**
- Average goals per match in top leagues: 2.5-2.8
- Over 2.5 hits approximately 50-55% in major leagues
''',
                'document_type': 'strategy',
            },
            {
                'title': 'Form Analysis in Football Betting',
                'content': '''
Form analysis examines recent performance to predict future results. Key considerations:

**Recent Form (Last 5-6 matches):**
- Win percentage
- Goals scored/conceded trends
- Home vs away form differences
- Quality of opposition faced

**Form Indicators:**
- WWWWW: Excellent form, high confidence
- WDWDW: Inconsistent, cautious betting
- LLLLL: Poor form, but potential for bounce-back

**Form Context:**
- Was a loss against a top team or relegation candidate?
- Are wins coming against weak opponents?
- Key player injuries or suspensions?
- Manager changes affecting performance?

**Statistical Weight:**
Recent form typically accounts for 30-40% of prediction confidence in most models.
''',
                'document_type': 'strategy',
            },
            {
                'title': 'Head-to-Head Analysis',
                'content': '''
Head-to-head (H2H) records between teams can reveal patterns:

**Why H2H Matters:**
- Some teams consistently perform well against specific opponents
- Playing styles may favor one team
- Psychological advantage from past victories

**H2H Considerations:**
- Minimum 3-5 recent meetings for relevance
- Consider venue (home/away)
- Account for squad changes
- Different competitions may yield different results

**H2H Limitations:**
- Old data (>2-3 years) less relevant
- Squad turnover invalidates patterns
- Different managers change dynamics
- Sample size issues with rare matchups

**Weighting in Models:**
H2H typically accounts for 10-15% of prediction models when sufficient data exists.
''',
                'document_type': 'strategy',
            },
            {
                'title': 'Understanding Betting Odds and Value',
                'content': '''
Betting odds represent implied probabilities. Understanding value is crucial:

**Converting Odds to Probability:**
- Decimal odds: Probability = 1 / odds
- Example: 2.50 odds = 40% implied probability

**Margin/Overround:**
Bookmakers build in profit margin. Total implied probabilities exceed 100%.
Example: Home 2.50 (40%) + Draw 3.50 (28.6%) + Away 2.80 (35.7%) = 104.3%

**Finding Value:**
Value exists when your assessed probability exceeds implied odds probability.
- Your probability: 50%
- Odds: 2.50 (40% implied)
- Value: 50% - 40% = 10% edge

**Kelly Criterion for Stake Sizing:**
Optimal stake = (bp - q) / b
Where: b = decimal odds - 1, p = your probability, q = 1 - p

**Risk Management:**
- Never bet entire bankroll
- Use fixed percentage staking (1-5%)
- Track all bets for analysis
''',
                'document_type': 'betting_guide',
            },
            {
                'title': 'Expected Goals (xG) Explained',
                'content': '''
Expected Goals (xG) is a statistical measure of chance quality:

**What xG Measures:**
- Likelihood of a shot resulting in a goal
- Based on historical shot data
- Factors: angle, distance, body part, assist type

**Interpreting xG:**
- xG > Goals: Underperforming, likely to improve
- xG < Goals: Overperforming, may regress
- Consistent xG/Goals ratio indicates true ability

**Using xG in Predictions:**
- Compare xG with actual goals over 10+ matches
- Teams with high xG but low goals are value bets
- Goalkeepers outperforming xG suggest quality

**xG Limitations:**
- Doesn't account for goalkeeper quality
- Shot quality can vary
- Small sample sizes unreliable
- Doesn't capture defensive pressure

**Model Integration:**
xG data improves prediction accuracy by 5-10% when incorporated properly.
''',
                'document_type': 'statistics',
            },
        ]

        # Create category
        category, _ = DocumentCategory.objects.get_or_create(
            slug='betting-strategy',
            defaults={
                'name': 'Betting Strategy',
                'description': 'Core betting strategy guides'
            }
        )

        created = 0
        updated = 0

        for strategy in strategies:
            doc, was_created = Document.objects.update_or_create(
                title=strategy['title'],
                document_type=strategy['document_type'],
                defaults={
                    'content': strategy['content'].strip(),
                    'category': category,
                    'author': 'Bet Hope System',
                    'metadata': {
                        'source_type': 'internal',
                        'updated_at': timezone.now().isoformat(),
                    }
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Documents: {created} created, {updated} updated'
        ))

        if embed:
            self.stdout.write('Embedding documents...')
            self._embed_documents()

    def _embed_documents(self):
        """Embed all documents."""
        try:
            from apps.documents.models import Document
            from apps.documents.services.embedding_service import EmbeddingService

            embedding_service = EmbeddingService()
            documents = Document.objects.filter(is_active=True)

            embedded = 0
            for doc in documents:
                try:
                    chunk_count = embedding_service.embed_document(doc.id)
                    self.stdout.write(f'  Embedded {doc.title}: {chunk_count} chunks')
                    embedded += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f'  Failed to embed {doc.title}: {e}'
                    ))

            self.stdout.write(self.style.SUCCESS(
                f'Embedded {embedded} documents'
            ))

        except ImportError as e:
            self.stdout.write(self.style.WARNING(
                f'Could not import embedding service: {e}'
            ))
