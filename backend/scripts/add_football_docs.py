"""
Add football knowledge documents for RAG
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.documents.models import Document

# Football betting knowledge documents
docs = [
    {
        'title': 'Home Advantage in Football',
        'content': '''Home advantage is one of the most significant factors in football predictions. Historically, home teams win approximately 45-46% of matches, with draws at 25-26% and away wins at 28-30%.

Key factors contributing to home advantage:
- Familiar surroundings and pitch conditions
- Crowd support and atmosphere
- Reduced travel fatigue
- Referee bias (slight tendency to favor home team)
- Tactical familiarity with home conditions

However, home advantage varies by league:
- Premier League: Home win rate ~45%
- La Liga: Home win rate ~47%
- Serie A: Home win rate ~44%
- Bundesliga: Home win rate ~43%

Teams with strong home records should be favored in predictions, but consider:
- Recent home form (last 5-10 matches)
- Quality of upcoming opponents
- Historical performance against specific teams
- Stadium atmosphere and capacity''',
        'document_type': 'betting_guide',
    },
    {
        'title': 'Form and Momentum in Football Betting',
        'content': '''Team form is a critical predictor of match outcomes. Recent performance often reflects current squad fitness, morale, and tactical effectiveness.

Key form indicators:
- Last 5-6 matches results (W/D/L)
- Points per game (PPG) in recent matches
- Goals scored and conceded trend
- Clean sheets or defensive vulnerabilities

Form patterns to consider:
- Winning streaks: Teams on 3+ consecutive wins have ~60% chance of winning next match
- Losing streaks: Teams on 3+ consecutive losses often see odds value as bookmakers overcorrect
- Unbeaten runs: Long unbeaten runs (5+ matches) indicate consistency

Form regression:
- Exceptional form (8+ wins from 10) tends to regress
- Very poor form (0-1 wins from 10) often improves
- Consider schedule difficulty when evaluating form

Momentum factors:
- Confidence after big wins
- Demoralization after heavy losses
- Cup competition distractions
- International break disruption''',
        'document_type': 'betting_guide',
    },
    {
        'title': 'Head-to-Head Analysis',
        'content': '''Historical head-to-head (H2H) records provide valuable context for predictions, though recent form typically matters more.

H2H considerations:
- Last 5-10 meetings between teams
- Home/away split in previous encounters
- Goal scoring patterns in H2H matches
- Recent H2H results (more relevant than older matches)

H2H limitations:
- Squad changes make old results less relevant
- Managerial changes can shift dynamics
- Different competition contexts (league vs cup)
- Sample size issues with infrequent matchups

When H2H matters most:
- Derby matches with consistent rivalry patterns
- Psychological advantages (teams with strong records against specific opponents)
- Tactical matchup tendencies

When to discount H2H:
- Significant squad rebuilds
- New manager appointments
- Promotion/relegation scenarios
- Results older than 3-4 seasons''',
        'document_type': 'betting_guide',
    },
    {
        'title': 'Understanding Betting Odds and Value',
        'content': '''Value betting is the cornerstone of profitable football betting. Value exists when the probability you assign to an outcome exceeds the implied probability from the odds.

Calculating implied probability:
- Decimal odds: 1 / odds = implied probability
- Example: 2.50 odds = 1/2.50 = 0.40 (40%)

Finding value:
- Compare your probability estimate to bookmaker implied probability
- Positive edge = your probability > implied probability
- Edge of 5%+ typically indicates value

Value bet thresholds:
- Strong value: Edge > 10%
- Moderate value: Edge 5-10%
- Marginal value: Edge 2-5%

Bankroll management:
- Kelly Criterion for stake sizing
- Never risk more than 1-5% of bankroll per bet
- Track ROI and review bet sizing regularly

Common value opportunities:
- Underdogs in matches between closely matched teams
- Away teams at inflated odds
- Under-rated teams with recent poor luck (xG vs actual)''',
        'document_type': 'strategy',
    },
    {
        'title': 'Expected Goals (xG) and Advanced Metrics',
        'content': '''Expected Goals (xG) measures the quality of chances created, providing deeper insight than just goals scored.

Understanding xG:
- xG assigns probability to each shot based on historical data
- Factors: distance, angle, body part, assist type, game state
- Team xG = sum of all shot xG values

Using xG in predictions:
- Compare xG to actual goals (overperformance/underperformance)
- xG regression: Teams significantly outperforming xG often regress
- xG difference (xGD) better predictor than goal difference

Advanced metrics:
- xGA: Expected goals against (defensive quality)
- npxG: Non-penalty expected goals
- xGOT: Expected goals on target
- PPDA: Passes per defensive action (pressing intensity)

Interpretation:
- High xG + low goals = Unlucky finishing, likely to improve
- Low xG + high goals = Unsustainable, likely to regress
- Consistent xG alignment = Reliable performance indicator

League-specific xG patterns:
- Premier League: Higher average xG due to open play
- Serie A: Lower xG, more defensive football
- Bundesliga: High xG, attacking style''',
        'document_type': 'statistics',
    },
    {
        'title': 'Risk Management in Football Betting',
        'content': '''Effective risk management separates successful bettors from recreational punters.

Key risk factors:
- Overconfidence in high-probability outcomes
- Underestimating draw probability
- Ignoring correlation in accumulators
- Chasing losses after bad runs

Risk mitigation strategies:
- Single bets over accumulators for serious betting
- Stake sizing based on confidence (1-5% of bankroll)
- Set loss limits per day/week/month
- Review and adjust strategy regularly

Match-specific risks:
- Derby matches: Unpredictable, emotion-driven
- End of season: Motivation varies significantly
- Early season: Limited form data
- Post-international break: Disrupted preparation

Red flags to avoid:
- Matches with injury/suspension uncertainty
- Extreme weather conditions
- Corruption concerns in certain leagues
- Managerial change within 1-2 matches

Psychological discipline:
- Avoid betting when emotional
- Stick to pre-defined criteria
- Accept variance as part of the process
- Long-term thinking over short-term results''',
        'document_type': 'strategy',
    },
]

def main():
    created = 0
    for doc in docs:
        d, was_created = Document.objects.get_or_create(
            title=doc['title'],
            defaults={
                'content': doc['content'],
                'document_type': doc['document_type'],
                'is_active': True,
            }
        )
        if was_created:
            created += 1
            print(f"Created: {doc['title']}")
        else:
            print(f"Exists: {doc['title']}")

    print(f"\nTotal created: {created}")
    print(f"Total documents: {Document.objects.count()}")

    # Now embed the documents
    print("\nEmbedding documents...")
    from apps.documents.services import EmbeddingService

    embedding_service = EmbeddingService()
    for doc in Document.objects.filter(is_active=True):
        try:
            num_chunks = embedding_service.embed_document(doc.id)
            print(f"Embedded {doc.title}: {num_chunks} chunks")
        except Exception as e:
            print(f"Error embedding {doc.title}: {e}")

if __name__ == '__main__':
    main()
