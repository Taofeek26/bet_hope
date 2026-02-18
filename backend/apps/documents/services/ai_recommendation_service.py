"""
AI Recommendation Service

Generates AI-powered recommendations using multiple LLM providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)

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
        'openai': 'gpt-4-turbo-preview',
        'anthropic': 'claude-3-sonnet-20240229',
        'google': 'gemini-pro',
    }

    # System prompts
    SYSTEM_PROMPT = """You are an expert football analyst AI assistant. Your role is to analyze match predictions and provide detailed, actionable recommendations.

When analyzing a prediction, you should:
1. Evaluate the prediction confidence and probabilities
2. Consider historical data and team statistics
3. Identify key factors that support or contradict the prediction
4. Provide a clear risk assessment
5. Give actionable recommendations

Be objective, data-driven, and clear about uncertainties. Always mention relevant statistics and form when available."""

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

    def generate_recommendation(
        self,
        prediction_id: int,
        include_rag: bool = True,
        model: Optional[str] = None,
    ) -> AIResponse:
        """
        Generate AI recommendation for a prediction.

        Args:
            prediction_id: Prediction ID
            include_rag: Whether to include RAG context
            model: Optional model override

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
        ai_rec = AIRecommendation.objects.create(
            prediction=prediction,
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
        )

        # Link context chunks
        if context_chunks:
            from apps.documents.models import DocumentChunk
            chunks = DocumentChunk.objects.filter(id__in=context_chunks)
            ai_rec.context_chunks.set(chunks)

        return parsed

    def _build_prompt(self, prediction, context: str) -> str:
        """Build the analysis prompt."""
        match = prediction.match

        # Calculate predicted total goals from individual scores if available
        predicted_goals = 0
        if prediction.predicted_home_score and prediction.predicted_away_score:
            predicted_goals = float(prediction.predicted_home_score) + float(prediction.predicted_away_score)

        prompt = f"""Analyze this football match prediction and provide detailed recommendations.

## Match Information
- **Match**: {match.home_team.name} vs {match.away_team.name}
- **Date**: {match.match_date}
- **League**: {match.season.league.name}
- **Prediction Strength**: {prediction.prediction_strength}
- **Model Version**: {prediction.model_version}
- **Model Type**: {prediction.model_type}

## Model Prediction
- **Predicted Outcome**: {self._outcome_label(prediction.recommended_outcome)}
- **Confidence**: {float(prediction.confidence_score) * 100:.1f}%
- **Home Win Probability**: {float(prediction.home_win_probability) * 100:.1f}%
- **Draw Probability**: {float(prediction.draw_probability) * 100:.1f}%
- **Away Win Probability**: {float(prediction.away_win_probability) * 100:.1f}%
- **Predicted Score**: {float(prediction.predicted_home_score or 0):.1f} - {float(prediction.predicted_away_score or 0):.1f}
- **Predicted Total Goals**: {predicted_goals:.1f}

"""

        # Add model key factors if available
        if prediction.key_factors:
            prompt += "## Model Key Factors\n"
            for factor in prediction.key_factors[:10]:
                if isinstance(factor, dict):
                    # Handle dictionary format
                    market = factor.get('market', 'unknown').replace('_', ' ').title()
                    prob = factor.get('probability', 0)
                    conf = factor.get('confidence', 'unknown')
                    prompt += f"- **{market}**: {prob*100:.1f}% probability ({conf} confidence)\n"
                else:
                    prompt += f"- {factor}\n"
            prompt += "\n"

        # Add feature data if available (summarized)
        if prediction.features_json:
            features = prediction.features_json
            prompt += "## Feature Summary\n"
            # Extract key features
            key_features = [
                ('home_form_points', 'Home Team Form Points'),
                ('away_form_points', 'Away Team Form Points'),
                ('home_goals_scored_avg', 'Home Goals Scored Avg'),
                ('away_goals_scored_avg', 'Away Goals Scored Avg'),
                ('home_goals_conceded_avg', 'Home Goals Conceded Avg'),
                ('away_goals_conceded_avg', 'Away Goals Conceded Avg'),
                ('h2h_home_wins', 'H2H Home Wins'),
                ('h2h_away_wins', 'H2H Away Wins'),
                ('h2h_draws', 'H2H Draws'),
                ('home_ppg', 'Home Points Per Game'),
                ('away_ppg', 'Away Points Per Game'),
            ]
            for key, label in key_features:
                if key in features:
                    prompt += f"- **{label}**: {features[key]}\n"
            prompt += "\n"



        if context:
            prompt += f"""## Relevant Context & Statistics
{context}

"""

        prompt += """## Your Analysis Required

Please provide:

1. **RECOMMENDATION**: Your overall assessment and recommended action based on the prediction. Be specific about what you recommend and why.

2. **CONFIDENCE ASSESSMENT**: Evaluate the model's confidence level. Is it justified based on the available data? What factors support or undermine this confidence?

3. **RISK ANALYSIS**: Identify potential risks and uncertainties. What could go wrong? What scenarios could invalidate the prediction?

4. **KEY FACTORS**: List 3-5 key factors that are most influential for this prediction (as a bullet list).

Format your response with clear section headers as shown above."""

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

    def _call_openai(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call OpenAI API."""
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7,
        )

        return {
            'content': response.choices[0].message.content,
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

        current_section = None
        current_content = []

        for line in content.split('\n'):
            line_lower = line.lower().strip()

            # Check for section headers
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

        # Save last section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()

        # Parse key factors as list
        if isinstance(sections['key_factors'], str):
            factors = []
            for line in sections['key_factors'].split('\n'):
                line = line.strip()
                if line.startswith(('-', '*', '•', '1', '2', '3', '4', '5')):
                    # Clean up bullet points
                    factor = line.lstrip('-*•0123456789. ').strip()
                    if factor:
                        factors.append(factor)
            sections['key_factors'] = factors[:5]

        return AIResponse(
            recommendation=sections['recommendation'] or content[:500],
            confidence_assessment=sections['confidence_assessment'],
            risk_analysis=sections['risk_analysis'],
            key_factors=sections['key_factors'],
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
        return providers
