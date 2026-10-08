"""
AI match previews (Phase 6): ~120 words for the day's biggest matches
(top 5 leagues + Champions League), written once from the same numbers the
AI analysis uses (all markets, prices, Elo, form, xG). About 1-2 US cents
each, at most MAX_PER_DAY a day.
"""
import logging
import os
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

BIG_LEAGUES = ['E0', 'SP1', 'I1', 'D1', 'F1', 'CL']
MAX_PER_DAY = 8
SYSTEM = (
    "You write short football match previews for a Nigerian betting audience. 110-130 words, plain text, "
    "no headings or bullet points. Cover: the form and strength of both teams, the most likely outcome and "
    "score, the one market the numbers point to (with its model chance and fair odds), and what the "
    "bookmakers' prices say. Use only the numbers given; never invent injuries, lineups or news. "
    "Finish with one short, honest caution. No stake advice."
)


def generate_previews(now=None, limit=MAX_PER_DAY):
    from apps.documents.services.ai_recommendation_service import AIRecommendationService
    from apps.matches.models import Match
    from apps.predictions.models import Prediction
    from .models import MatchPreview

    key = os.getenv('OPENROUTER_API_KEY')
    if not key:
        return 0
    now = now or timezone.now()
    preds = (Prediction.objects.filter(model_version__startswith='v2_', match__status=Match.Status.SCHEDULED,
                                       match__season__league__code__in=BIG_LEAGUES,
                                       match__kickoff_at__gt=now, match__kickoff_at__lte=now + timedelta(hours=48))
             .filter(Q(match__ai_preview__isnull=True) | Q(match__ai_preview__updated_at__lt=now - timedelta(hours=24)))
             .select_related('match__home_team', 'match__away_team', 'match__season__league')
             .prefetch_related('match__bookmaker_prices'))
    # Biggest first: the two teams' combined Elo rating.
    def elo(p):
        f = p.features_json or {}
        return (f.get('elo_home') or 0) + (f.get('elo_away') or 0)
    chosen, seen = [], set()
    for p in sorted(preds, key=elo, reverse=True):
        if p.match_id not in seen:
            seen.add(p.match_id)
            chosen.append(p)
        if len(chosen) >= limit:
            break
    if not chosen:
        return 0

    import openai
    client = openai.OpenAI(api_key=key, base_url='https://openrouter.ai/api/v1')
    svc = AIRecommendationService.__new__(AIRecommendationService)
    model = AIRecommendationService.MODELS['openrouter']
    made = 0
    for p in chosen:
        data = svc._build_prompt(p, '').split('## TASK')[0]
        try:
            text = ''
            for _ in range(2):  # reasoning model: retry once on an empty reply
                r = client.chat.completions.create(model=model, max_tokens=6000, temperature=0.6, messages=[
                    {'role': 'system', 'content': SYSTEM},
                    {'role': 'user', 'content': data + '\n## TASK\nWrite the preview.'}])
                text = (r.choices[0].message.content or '').strip()
                if text:
                    break
            if not text:
                continue
            MatchPreview.objects.update_or_create(match=p.match, defaults={
                'text': text[:2000], 'model_name': model, 'prediction_version': p.model_version})
            made += 1
        except Exception as e:
            logger.warning(f'Preview for match {p.match_id} failed: {e}')
    return made
