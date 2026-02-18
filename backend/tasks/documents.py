"""
Document Tasks

Tasks for scraping betting/football documentation and updating embeddings.
Runs daily to keep the RAG knowledge base up to date.
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

# Documentation sources to scrape
DOCUMENTATION_SOURCES = [
    {
        'url': 'https://www.football-data.co.uk/notes.txt',
        'title': 'Football-Data.co.uk Notes and Data Dictionary',
        'document_type': 'statistics',
        'category': 'data_dictionary',
    },
]

# Football news RSS feeds
FOOTBALL_NEWS_FEEDS = [
    {
        'url': 'https://www.espn.com/espn/rss/soccer/news',  # ESPN Soccer
        'source': 'ESPN',
        'category': 'news',
    },
    {
        'url': 'https://www.skysports.com/rss/12040',  # Sky Sports (general but includes football)
        'source': 'Sky Sports',
        'category': 'news',
    },
    {
        'url': 'https://feeds.bbci.co.uk/sport/football/rss.xml',  # BBC Sport Football
        'source': 'BBC Sport',
        'category': 'news',
    },
]

# Betting strategy content to embed
BETTING_STRATEGIES = [
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


@shared_task(bind=True, max_retries=2, default_retry_delay=600)
def scrape_documentation(self):
    """
    Scrape documentation from external sources.
    Runs daily at 4:00 AM UTC.
    """
    logger.info("Starting documentation scraping...")

    try:
        import requests
        from apps.documents.models import Document, DocumentCategory

        scraped = 0
        errors = []

        for source in DOCUMENTATION_SOURCES:
            try:
                response = requests.get(source['url'], timeout=30)
                response.raise_for_status()

                content = response.text

                # Get or create category
                category, _ = DocumentCategory.objects.get_or_create(
                    slug=source.get('category', 'general'),
                    defaults={'name': source.get('category', 'General').replace('_', ' ').title()}
                )

                # Update or create document
                doc, created = Document.objects.update_or_create(
                    source_url=source['url'],
                    defaults={
                        'title': source['title'],
                        'content': content,
                        'document_type': source['document_type'],
                        'category': category,
                        'metadata': {
                            'scraped_at': timezone.now().isoformat(),
                            'source_type': 'external',
                        }
                    }
                )

                scraped += 1
                action = 'Created' if created else 'Updated'
                logger.info(f"{action} document: {source['title']}")

            except Exception as e:
                errors.append(f"{source['url']}: {str(e)}")
                logger.error(f"Failed to scrape {source['url']}: {e}")

        logger.info(f"Documentation scraping completed: {scraped} documents")

        return {
            'status': 'success' if not errors else 'partial',
            'scraped': scraped,
            'errors': errors,
        }

    except Exception as e:
        logger.error(f"Documentation scraping failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def update_strategy_documents(self):
    """
    Update built-in strategy documents.
    Ensures core betting knowledge is always available.
    """
    logger.info("Updating strategy documents...")

    try:
        from apps.documents.models import Document, DocumentCategory

        # Get or create strategy category
        category, _ = DocumentCategory.objects.get_or_create(
            slug='betting-strategy',
            defaults={'name': 'Betting Strategy', 'description': 'Core betting strategy guides'}
        )

        updated = 0

        for strategy in BETTING_STRATEGIES:
            doc, created = Document.objects.update_or_create(
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
            updated += 1

        logger.info(f"Updated {updated} strategy documents")

        return {
            'status': 'success',
            'updated': updated,
        }

    except Exception as e:
        logger.error(f"Strategy document update failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=180)
def embed_documents(self, document_ids=None, force_reembed=False):
    """
    Generate embeddings for documents.

    Args:
        document_ids: Optional list of specific document IDs to embed
        force_reembed: If True, re-embed even if chunks exist
    """
    logger.info("Starting document embedding...")

    try:
        from apps.documents.models import Document
        from apps.documents.services.embedding_service import EmbeddingService

        embedding_service = EmbeddingService()

        # Get documents to embed
        if document_ids:
            documents = Document.objects.filter(id__in=document_ids, is_active=True)
        else:
            # Get documents without chunks or that need re-embedding
            if force_reembed:
                documents = Document.objects.filter(is_active=True)
            else:
                documents = Document.objects.filter(
                    is_active=True,
                    chunks__isnull=True
                ).distinct()

        embedded = 0
        total_chunks = 0
        errors = []

        for doc in documents:
            try:
                chunk_count = embedding_service.embed_document(doc.id)
                embedded += 1
                total_chunks += chunk_count
                logger.info(f"Embedded document {doc.id}: {chunk_count} chunks")
            except Exception as e:
                errors.append(f"Document {doc.id}: {str(e)}")
                logger.error(f"Failed to embed document {doc.id}: {e}")

        logger.info(f"Document embedding completed: {embedded} documents, {total_chunks} chunks")

        return {
            'status': 'success' if not errors else 'partial',
            'embedded': embedded,
            'total_chunks': total_chunks,
            'errors': errors,
        }

    except Exception as e:
        logger.error(f"Document embedding failed: {e}")
        raise self.retry(exc=e)


@shared_task
def refresh_all_documents(include_news=True):
    """
    Full document refresh pipeline.
    Runs daily to keep RAG knowledge base current.

    Pipeline:
    1. Scrape external documentation
    2. Update internal strategy documents
    3. Scrape football news (if enabled)
    4. Generate embeddings for all documents
    """
    logger.info("Starting full document refresh...")

    results = {
        'started_at': timezone.now().isoformat(),
        'steps': {}
    }

    try:
        # Step 1: Scrape external docs
        scrape_result = scrape_documentation.delay()
        results['steps']['scrape'] = 'queued'

        # Step 2: Update strategy docs
        strategy_result = update_strategy_documents.delay()
        results['steps']['strategy'] = 'queued'

        # Step 3: Scrape football news
        if include_news:
            news_result = scrape_football_news.delay()
            results['steps']['news'] = 'queued'

        # Step 4: Embed documents (chained to run after updates)
        from celery import chain

        embed_chain = chain(
            update_strategy_documents.s(),
            embed_documents.si(force_reembed=False)
        )
        embed_chain.delay()
        results['steps']['embed'] = 'queued'

        results['status'] = 'success'
        results['completed_at'] = timezone.now().isoformat()

        logger.info("Full document refresh pipeline started")

        return results

    except Exception as e:
        logger.error(f"Document refresh failed: {e}")
        results['status'] = 'error'
        results['error'] = str(e)
        return results


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def scrape_football_news(self, max_articles_per_feed=10):
    """
    Scrape latest football news from RSS feeds.
    Runs twice daily at 6:00 AM and 6:00 PM UTC.
    """
    logger.info("Scraping football news...")

    try:
        import feedparser
        from apps.documents.models import Document, DocumentCategory

        # Get or create news category
        category, _ = DocumentCategory.objects.get_or_create(
            slug='football-news',
            defaults={'name': 'Football News', 'description': 'Latest football news and updates'}
        )

        scraped = 0
        errors = []

        for feed_config in FOOTBALL_NEWS_FEEDS:
            try:
                feed = feedparser.parse(feed_config['url'])

                if feed.bozo and not feed.entries:
                    errors.append(f"{feed_config['source']}: Failed to parse feed")
                    continue

                for entry in feed.entries[:max_articles_per_feed]:
                    try:
                        # Extract content
                        title = entry.get('title', 'Untitled')

                        # Get content from summary or content field
                        content = ''
                        if hasattr(entry, 'content') and entry.content:
                            content = entry.content[0].get('value', '')
                        elif hasattr(entry, 'summary'):
                            content = entry.summary
                        elif hasattr(entry, 'description'):
                            content = entry.description

                        # Skip if no content
                        if not content or len(content) < 100:
                            continue

                        # Clean HTML tags (basic)
                        import re
                        content = re.sub(r'<[^>]+>', '', content)
                        content = content.strip()

                        # Get link
                        link = entry.get('link', '')

                        # Get published date
                        published = None
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            from datetime import datetime
                            published = datetime(*entry.published_parsed[:6])

                        # Check if article already exists (by URL)
                        if link and Document.objects.filter(source_url=link).exists():
                            continue

                        # Create document
                        doc = Document.objects.create(
                            title=f"[{feed_config['source']}] {title}",
                            content=content,
                            document_type='news',
                            category=category,
                            source_url=link,
                            author=feed_config['source'],
                            metadata={
                                'source': feed_config['source'],
                                'scraped_at': timezone.now().isoformat(),
                                'published_at': published.isoformat() if published else None,
                                'type': 'news_article',
                            }
                        )
                        scraped += 1
                        logger.info(f"Scraped: {title[:50]}...")

                    except Exception as e:
                        logger.warning(f"Failed to process article: {e}")

            except Exception as e:
                errors.append(f"{feed_config['source']}: {str(e)}")
                logger.error(f"Failed to scrape {feed_config['source']}: {e}")

        logger.info(f"Football news scraping completed: {scraped} articles")

        return {
            'status': 'success' if not errors else 'partial',
            'scraped': scraped,
            'errors': errors,
        }

    except ImportError:
        logger.error("feedparser not installed. Run: pip install feedparser")
        return {'status': 'error', 'message': 'feedparser not installed'}
    except Exception as e:
        logger.error(f"Football news scraping failed: {e}")
        raise self.retry(exc=e)


@shared_task
def cleanup_old_news(days_to_keep=7):
    """
    Remove old news articles to keep the RAG focused on recent news.
    Runs daily.
    """
    logger.info("Cleaning up old news articles...")

    try:
        from apps.documents.models import Document

        cutoff = timezone.now() - timedelta(days=days_to_keep)

        # Delete old news articles
        deleted, _ = Document.objects.filter(
            document_type='news',
            created_at__lt=cutoff
        ).delete()

        logger.info(f"Deleted {deleted} old news articles")

        return {
            'status': 'success',
            'deleted': deleted,
        }

    except Exception as e:
        logger.error(f"News cleanup failed: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_old_embeddings():
    """
    Clean up stale embedding cache entries.
    Runs weekly.
    """
    logger.info("Cleaning up old embeddings...")

    try:
        from apps.documents.models import EmbeddingCache

        # Delete cache entries older than 30 days
        cutoff = timezone.now() - timedelta(days=30)
        deleted, _ = EmbeddingCache.objects.filter(created_at__lt=cutoff).delete()

        logger.info(f"Deleted {deleted} old embedding cache entries")

        return {
            'status': 'success',
            'deleted': deleted,
        }

    except Exception as e:
        logger.error(f"Embedding cleanup failed: {e}")
        return {'status': 'error', 'message': str(e)}
