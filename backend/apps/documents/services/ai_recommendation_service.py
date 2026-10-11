"""
AI Recommendation Service

Generates AI-powered recommendations using multiple LLM providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- OpenRouter (routes to Claude/GPT/etc. through one key + one API shape)

Uses RAG context for enhanced recommendations.
"""
import logging
import time
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Try to import AI clients
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

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class AIProvider(str, Enum):
    OPENAI = 'openai'
    ANTHROPIC = 'anthropic'
    GOOGLE = 'google'
    OPENROUTER = 'openrouter'


@dataclass
class AIResponse:
    """Response from AI provider."""
    recommendation: str
    confidence_assessment: str
    risk_analysis: str
    key_factors: List[str]
    tokens_used: int
    provider: str
    model: str


class AIRecommendationService:
    """
    Service for generating AI-powered match recommendations.

    Integrates with multiple LLM providers and uses RAG for context.
    """

    # Default models per provider
    MODELS = {
        'openai': 'gpt-3.5-turbo',  # Using 3.5-turbo for faster response and lower memory usage
        'anthropic': 'claude-sonnet-5',
        'google': 'gemini-pro',
        # OpenRouter model slugs are "vendor/model" regardless of which
        # vendor is actually serving the request underneath.
        # Only DeepSeek endpoints clear this account's OpenRouter privacy/
        # data-policy restrictions (Settings > Privacy) — confirmed by
        # testing Claude, GPT-4o-mini, and 5 other DeepSeek slugs, which
        # all hit "No endpoints available matching your guardrail
        # restrictions" even with a healthy account balance.
        'openrouter': 'deepseek/deepseek-v4-pro',
    }

    # System prompts
    SYSTEM_PROMPT = """You are a careful football betting analyst. You get the model's probabilities for EVERY market of one match (result, double chance, draw no bet, GG/NG, over/under, team goals, clean sheets, correct score), each with fair odds and, where known, the best bookmaker price and the edge. Pick the most sensible bet across ALL markets, or say there isn't one.

RESPONSE FORMAT (follow exactly):
```
📊 BET RECOMMENDATION
━━━━━━━━━━━━━━━━━━━━
🎯 Pick: [market and selection, e.g. "Double chance 1X" or "Over 2.5 goals", or "No bet"]
💰 Stake: [0-2 units; 0 when no price beats fair odds] · only at odds ≥ [fair odds]
📈 Confidence: [LOW/MEDIUM/HIGH]

📋 QUICK ANALYSIS
• [Why this market: model chance vs price, citing the numbers]
• [Second-best market or a safer alternative, with its numbers]
• [What the form / Elo / expected-goals data says]
• [A market to avoid and why]

📚 SOURCES USED
• Model: [the probabilities and fair odds you used]
• [Document name, if a knowledge-base document was used]

⚠️ RISK: [One sentence]
```

RULES:
- Max 180 words. Bullet points only.
- Use only the numbers given. Never invent odds, injuries or news.
- A bet is only good value if the price is ABOVE the fair odds (positive edge). If no price is known, give the minimum odds instead ("only at odds ≥ X").
- Prefer markets marked TESTED (result, double chance, draw no bet, over/under 2.5). Say so when you use an ESTIMATE market, and avoid correct score unless asked.
- The model is about level with the bookmakers overall, so "No bet" is a valid, often correct answer. Never call a bet a sure thing.
- Higher probability does not mean better value: compare chance with price."""

    def __init__(self, provider: str = 'openai'):
        """
        Initialize the AI service.

        Args:
            provider: AI provider to use ('openai', 'anthropic', 'google')
        """
        self.provider = provider
        self._validate_provider()
        self._init_clients()

    def _validate_provider(self):
        """Validate the provider is available."""
        if self.provider == 'openai' and not OPENAI_AVAILABLE:
            raise ImportError("OpenAI not available. Install with: pip install openai")
        if self.provider == 'anthropic' and not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic not available. Install with: pip install anthropic")
        if self.provider == 'google' and not GOOGLE_AVAILABLE:
            raise ImportError("Google AI not available. Install with: pip install google-generativeai")
        # OpenRouter speaks the OpenAI Chat Completions API — same package,
        # different base_url, so it rides on the same availability check.
        if self.provider == 'openrouter' and not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not available (required for OpenRouter too). Install with: pip install openai")

    def _init_clients(self):
        """Initialize AI clients."""
        if self.provider == 'openai':
            self.client = openai.OpenAI(
                api_key=getattr(settings, 'OPENAI_API_KEY', None)
            )
        elif self.provider == 'anthropic':
            self.client = anthropic.Anthropic(
                api_key=getattr(settings, 'ANTHROPIC_API_KEY', None)
            )
        elif self.provider == 'google':
            genai.configure(api_key=getattr(settings, 'GOOGLE_API_KEY', None))
            self.client = genai.GenerativeModel(self.MODELS['google'])
        elif self.provider == 'openrouter':
            self.client = openai.OpenAI(
                api_key=getattr(settings, 'OPENROUTER_API_KEY', None),
                base_url='https://openrouter.ai/api/v1',
            )

    def generate_recommendation(
        self,
        prediction_id: int,
        include_rag: bool = True,
        model: Optional[str] = None,
        record=None,
    ) -> AIResponse:
        """
        Generate AI recommendation for a prediction.

        Args:
            prediction_id: Prediction ID
            include_rag: Whether to include RAG context
            model: Optional model override
            record: Optional existing AIRecommendation row (status
                pending/processing) to fill in instead of creating a new
                one — used by the async path (generate_ai_recommendation
                command run in the manage Lambda).

        Returns:
            AIResponse with recommendation details
        """
        from apps.predictions.models import Prediction
        from apps.documents.models import AIRecommendation
        from .rag_service import RAGService

        start_time = time.time()

        # Get prediction
        prediction = Prediction.objects.select_related(
            'match', 'match__home_team', 'match__away_team',
            'match__season__league'
        ).get(id=prediction_id)

        # Build context
        context = ""
        context_chunks = []

        if include_rag:
            try:
                rag_service = RAGService()
                results = rag_service.retrieve_for_prediction(prediction, top_k=5)
                context = rag_service.build_context(results, max_tokens=2000)
                context_chunks = [r.chunk_id for r in results]

                # Add team stats
                stats = rag_service.get_relevant_stats(
                    prediction.match.home_team_id,
                    prediction.match.away_team_id
                )
                if stats:
                    context += f"\n\n---\n\nCurrent Statistics:\n{json.dumps(stats, indent=2)}"
            except Exception as e:
                logger.warning(f"RAG retrieval failed, continuing without context: {e}")
                context = ""
                context_chunks = []

        # Build prompt
        prompt = self._build_prompt(prediction, context)

        # Call AI provider
        model = model or self.MODELS[self.provider]
        response = self._call_ai(prompt, model)

        # Parse response
        parsed = self._parse_response(response['content'])

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Save to database
        fields = dict(
            provider=self.provider,
            model_name=model,
            prompt=prompt,
            response=response['content'],
            status=AIRecommendation.Status.COMPLETED,
            context_summary=context[:1000] if context else '',
            recommendation=parsed.recommendation,
            confidence_assessment=parsed.confidence_assessment,
            risk_analysis=parsed.risk_analysis,
            key_factors=parsed.key_factors,
            tokens_used=response.get('tokens', 0),
            processing_time_ms=processing_time,
            error_message='',
        )
        if record is not None:
            for name, value in fields.items():
                setattr(record, name, value)
            record.save()
            ai_rec = record
        else:
            ai_rec = AIRecommendation.objects.create(prediction=prediction, **fields)

        # Link context chunks
        if context_chunks:
            from apps.documents.models import DocumentChunk
            chunks = DocumentChunk.objects.filter(id__in=context_chunks)
            ai_rec.context_chunks.set(chunks)

        return parsed

    def _build_prompt(self, prediction, context: str) -> str:
        """The analysis prompt: every market for the match, with prices (Phase 5)."""
        from apps.predictions.markets import build_markets
        match = prediction.match
        home, away = match.home_team.name, match.away_team.name
        pct = lambda x: f"{float(x) * 100:.1f}%"

        # Best bookmaker 1X2 prices (The Odds API) and the market average.
        best = {}
        books = [b for b in match.bookmaker_prices.all() if not b.is_exchange]
        for side in ('home', 'draw', 'away'):
            if books:
                top = max(books, key=lambda b: getattr(b, f'{side}_odds'))
                best[side] = {'odds': float(getattr(top, f'{side}_odds')), 'bookmaker': top.title}
        avg = getattr(match, 'odds', None)
        markets = build_markets(prediction, home, away, best_1x2=best, avg_odds=avg)

        f = prediction.features_json or {}
        def feat(key, fmt='{:.2f}'):
            v = f.get(key)
            return fmt.format(v) if isinstance(v, (int, float)) else 'n/a'

        kickoff = match.kickoff_at.strftime('%Y-%m-%d %H:%M UTC') if match.kickoff_at else str(match.match_date)
        prompt = f"""Analyse every market for this match and recommend the best bet, or "No bet".

## Match
- {home} vs {away} · {match.season.league.name} · {kickoff}
- Model: {prediction.model_version} ({'used bookmaker odds as an input' if f.get('used_odds') else 'no odds available as input'})

## Model result probabilities (tested on 8,106 unseen matches: 50.3% accuracy, well calibrated)
- {home} win {pct(prediction.home_win_probability)} · Draw {pct(prediction.draw_probability)} · {away} win {pct(prediction.away_win_probability)}
- Expected goals: {home} {feat('xg_home')} · {away} {feat('xg_away')} · most likely score {int(prediction.predicted_home_score or 0)}-{int(prediction.predicted_away_score or 0)}

## Form and strength (before this match)
- Elo rating: {home} {feat('elo_home', '{:.0f}')} · {away} {feat('elo_away', '{:.0f}')}
- Points per game, last 5: {home} {feat('h_ppg5')} · {away} {feat('a_ppg5')}
- Points per game, this season: {home} {feat('h_season_ppg')} · {away} {feat('a_season_ppg')}
- Shots on target per game, last 10: {home} {feat('h_sot10', '{:.1f}')} · {away} {feat('a_sot10', '{:.1f}')}
"""
        if avg and avg.home_odds and avg.draw_odds and avg.away_odds:
            prompt += (f"- Market average odds: {float(avg.home_odds):.2f} / {float(avg.draw_odds):.2f} / {float(avg.away_odds):.2f} "
                       f"(from {avg.bookmaker})\n")

        prompt += "\n## All markets: model chance · fair odds (no margin) · best price · edge\n"
        group = None
        for m in markets:
            if m['group'] != group:
                group = m['group']
                prompt += f"\n**{group}**\n"
            price = (f"best {m['best_odds']:.2f} ({m['best_bookmaker']}), edge {m['edge'] * 100:+.1f} pts"
                     if m['best_odds'] else 'no price known')
            prompt += (f"- {m['label']}: {m['probability'] * 100:.1f}% · fair {m['fair_odds']:.2f} · {price} · "
                       f"{'TESTED' if m['tested'] else 'ESTIMATE'}\n")

        positive = [m for m in markets if m['edge'] is not None and m['edge'] > 0]
        prompt += ("\n## Markets priced above fair odds\n" + (
            '\n'.join(f"- {m['label']}: edge {m['edge'] * 100:+.1f} pts at {m['best_odds']:.2f}" for m in positive)
            if positive else "- None of the priced markets beats the model's fair odds."))

        if context:
            prompt += f"\n\n## 📚 Knowledge base documents\n{context}\n"
        prompt += """

## TASK
Use the EXACT format from your system prompt. Compare all markets, not just the match result. Recommend at most one bet (or "No bet"), give one alternative, and name one market to avoid."""
        return prompt

    def _outcome_label(self, outcome: str) -> str:
        """Convert outcome code to label."""
        labels = {'H': 'Home Win', 'D': 'Draw', 'A': 'Away Win'}
        return labels.get(outcome, outcome)

    def _call_ai(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call the AI provider."""
        if self.provider == 'openai':
            return self._call_openai(prompt, model)
        elif self.provider == 'anthropic':
            return self._call_anthropic(prompt, model)
        elif self.provider == 'google':
            return self._call_google(prompt, model)
        elif self.provider == 'openrouter':
            # OpenRouter is Chat-Completions-API-compatible, same request
            # shape as OpenAI — no separate call method needed.
            return self._call_openai(prompt, model)

    def _call_openai(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call OpenAI API (also used for OpenRouter — same request shape)."""
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            # Reasoning models routed through OpenRouter (e.g. deepseek-v4-pro)
            # spend a large chunk of their token budget on internal
            # chain-of-thought before the visible answer — 359 reasoning
            # tokens just to say "hi" in 3 words in testing. 2000 was
            # regularly getting exhausted mid-reasoning, returning an empty
            # content string. Plain chat models just ignore the headroom.
            max_tokens=4000,
            temperature=0.7,
        )

        return {
            'content': response.choices[0].message.content or '',
            'tokens': response.usage.total_tokens,
        }

    def _call_anthropic(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call Anthropic API."""
        response = self.client.messages.create(
            model=model,
            max_tokens=2000,
            system=self.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return {
            'content': response.content[0].text,
            'tokens': response.usage.input_tokens + response.usage.output_tokens,
        }

    def _call_google(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call Google Gemini API."""
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}"
        response = self.client.generate_content(full_prompt)

        return {
            'content': response.text,
            'tokens': 0,  # Gemini doesn't return token count easily
        }

    def _parse_response(self, content: str) -> AIResponse:
        """Parse AI response into structured format."""
        sections = {
            'recommendation': '',
            'confidence_assessment': '',
            'risk_analysis': '',
            'key_factors': [],
        }

        # Remove code block markers
        content = content.replace('```', '').strip()

        # For the new betting format, parse differently
        lines = content.split('\n')

        # Extract bet recommendation section
        bet_lines = []
        analysis_lines = []
        sources_lines = []
        risk_line = ''

        current_section = None

        for line in lines:
            line_stripped = line.strip()

            # Skip empty lines and decorative lines
            if not line_stripped or line_stripped.startswith('━'):
                continue

            # Detect sections by emoji or keywords
            if 'BET RECOMMENDATION' in line:
                current_section = 'bet'
            elif 'QUICK ANALYSIS' in line:
                current_section = 'analysis'
            elif 'SOURCES' in line:
                current_section = 'sources'
            elif '⚠️' in line or 'RISK:' in line:
                current_section = 'risk'
                # Extract risk text from same line
                risk_text = line_stripped.replace('⚠️', '').replace('RISK:', '').strip()
                if risk_text:
                    risk_line = risk_text
            elif current_section == 'bet' and ('🎯' in line or '💰' in line or '📈' in line or 'Pick:' in line or 'Stake:' in line or 'Confidence:' in line):
                bet_lines.append(line_stripped)
            elif current_section == 'analysis' and (line_stripped.startswith('•') or line_stripped.startswith('-')):
                analysis_lines.append(line_stripped.lstrip('•- '))
            elif current_section == 'sources' and (line_stripped.startswith('•') or line_stripped.startswith('-')):
                sources_lines.append(line_stripped.lstrip('•- '))
            elif current_section == 'risk' and line_stripped and not risk_line:
                risk_line = line_stripped

        # Build recommendation from bet section (formatted nicely)
        if bet_lines:
            recommendation = "📊 BET RECOMMENDATION\n" + '\n'.join(bet_lines)
        else:
            recommendation = content[:500]

        # Build confidence from sources (references model)
        if sources_lines:
            confidence = "📚 Sources:\n• " + '\n• '.join(sources_lines)
        else:
            confidence = ''

        # Key factors from analysis
        key_factors = analysis_lines[:5] if analysis_lines else []

        # Risk analysis
        risk_analysis = f"⚠️ {risk_line}" if risk_line else ''

        # Fallback parsing for old format
        if not bet_lines:
            current_section = None
            current_content = []

            for line in lines:
                line_lower = line.lower().strip()

                if 'recommendation' in line_lower and ('**' in line or '#' in line):
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    current_section = 'recommendation'
                    current_content = []
                elif 'confidence' in line_lower and ('**' in line or '#' in line):
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    current_section = 'confidence_assessment'
                    current_content = []
                elif 'risk' in line_lower and ('**' in line or '#' in line):
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    current_section = 'risk_analysis'
                    current_content = []
                elif 'key factor' in line_lower and ('**' in line or '#' in line):
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    current_section = 'key_factors'
                    current_content = []
                elif current_section:
                    current_content.append(line)

            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content).strip()

            if isinstance(sections['key_factors'], str):
                factors = []
                for line in sections['key_factors'].split('\n'):
                    line = line.strip()
                    if line.startswith(('-', '*', '•', '1', '2', '3', '4', '5')):
                        factor = line.lstrip('-*•0123456789. ').strip()
                        if factor:
                            factors.append(factor)
                sections['key_factors'] = factors[:5]

            recommendation = sections['recommendation'] or content[:500]
            confidence = sections['confidence_assessment']
            risk_analysis = sections['risk_analysis']
            key_factors = sections['key_factors']

        return AIResponse(
            recommendation=recommendation,
            confidence_assessment=confidence,
            risk_analysis=risk_analysis,
            key_factors=key_factors,
            tokens_used=0,
            provider=self.provider,
            model=self.MODELS[self.provider],
        )

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available AI providers."""
        providers = []
        if OPENAI_AVAILABLE and getattr(settings, 'OPENAI_API_KEY', None):
            providers.append('openai')
        if ANTHROPIC_AVAILABLE and getattr(settings, 'ANTHROPIC_API_KEY', None):
            providers.append('anthropic')
        if GOOGLE_AVAILABLE and getattr(settings, 'GOOGLE_API_KEY', None):
            providers.append('google')
        if OPENAI_AVAILABLE and getattr(settings, 'OPENROUTER_API_KEY', None):
            providers.append('openrouter')
        return providers
