"""
News Signal Extraction Service

Turns recent team-tagged news Documents into structured, numeric signals
that feed INTO the ML pipeline as features (see
apps/ml_pipeline/features/match_features.py::_get_ai_signal_features).

This is the missing feedback path the RAG/AI layer didn't have before:
AIRecommendationService (ai_recommendation_service.py) reads an already
-generated Prediction and produces after-the-fact explanatory text — it
never influences training/inference. This service runs upstream of
predictions instead, turning news text into an injury-mention score and
a sentiment score that become model input features.
"""
import json
import logging
from datetime import date, timedelta
from typing import Optional, Dict, Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


SYSTEM_PROMPT = """You are a football news analyst. Given recent news headlines/snippets
about one team, output ONLY a JSON object (no prose, no markdown) with exactly these keys:

{"injury_mention_score": <float 0.0-1.0>, "sentiment_score": <float -1.0 to 1.0>}

injury_mention_score: how strongly the articles mention injuries, suspensions, or key
player unavailability for this team (0.0 = none mentioned, 1.0 = multiple/severe).

sentiment_score: overall tone/morale implied by the articles for this team
(-1.0 = very negative/disruption, 0.0 = neutral, 1.0 = very positive)."""


class NewsSignalExtractionService:
    """Extracts injury/sentiment signals from a team's recent tagged news."""

    LOOKBACK_DAYS = 7
    MIN_ARTICLES = 1
    MAX_ARTICLES = 8

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or getattr(settings, 'DEFAULT_AI_PROVIDER', 'openai')
        if self.provider == 'openai' and not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed")
        if self.provider == 'anthropic' and not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed")

        if self.provider == 'openai':
            self.client = openai.OpenAI(api_key=getattr(settings, 'OPENAI_API_KEY', None))
        elif self.provider == 'anthropic':
            self.client = anthropic.Anthropic(api_key=getattr(settings, 'ANTHROPIC_API_KEY', None))
        else:
            raise ValueError(f"Unsupported provider for news signal extraction: {self.provider}")

    def generate_for_team(self, team, as_of: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """
        Generate (and persist) a TeamNewsSignal for one team from its
        recent tagged news Documents. Returns None if there's not enough
        recent news to bother calling the LLM (avoids wasting API calls
        and avoids a signal built on a single throwaway mention).
        """
        from apps.documents.models import Document, TeamNewsSignal

        as_of = as_of or timezone.now().date()
        since = timezone.now() - timedelta(days=self.LOOKBACK_DAYS)

        articles = list(
            Document.objects.filter(
                teams=team, document_type='news', created_at__gte=since
            ).order_by('-created_at')[:self.MAX_ARTICLES]
        )

        if len(articles) < self.MIN_ARTICLES:
            return None

        prompt = self._build_prompt(team.name, articles)

        try:
            content = self._call(prompt)
            parsed = self._parse_json(content)
        except Exception as e:
            logger.error(f"News signal extraction failed for {team.name}: {e}")
            return None

        signal, _ = TeamNewsSignal.objects.update_or_create(
            team=team,
            as_of_date=as_of,
            defaults={
                'injury_mention_score': max(0.0, min(1.0, float(parsed.get('injury_mention_score', 0.0)))),
                'sentiment_score': max(-1.0, min(1.0, float(parsed.get('sentiment_score', 0.0)))),
                'source_count': len(articles),
                'provider': self.provider,
            }
        )
        return {
            'team': team.name,
            'injury_mention_score': signal.injury_mention_score,
            'sentiment_score': signal.sentiment_score,
            'source_count': signal.source_count,
        }

    def _build_prompt(self, team_name: str, articles: list) -> str:
        snippets = "\n".join(
            f"- {a.title}: {a.content[:300]}" for a in articles
        )
        return f"Team: {team_name}\n\nRecent articles:\n{snippets}"

    def _call(self, prompt: str) -> str:
        if self.provider == 'openai':
            response = self.client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=100,
                temperature=0.2,
            )
            return response.choices[0].message.content
        elif self.provider == 'anthropic':
            response = self.client.messages.create(
                model='claude-3-haiku-20240307',
                max_tokens=100,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        raise ValueError(f"Unsupported provider: {self.provider}")

    @staticmethod
    def _parse_json(content: str) -> Dict[str, Any]:
        """Extract the first JSON object from the response, tolerating
        stray markdown fences or extra text some models add despite
        instructions."""
        content = content.strip()
        start = content.find('{')
        end = content.rfind('}')
        if start == -1 or end == -1:
            raise ValueError(f"No JSON object found in response: {content[:200]}")
        return json.loads(content[start:end + 1])
