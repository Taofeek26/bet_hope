"""
RAG (Retrieval Augmented Generation) Service

Handles document retrieval using vector similarity search.
"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from django.db.models import Q
from pgvector.django import CosineDistance

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from document retrieval."""
    chunk_id: int
    document_id: int
    document_title: str
    content: str
    score: float
    metadata: Dict[str, Any]


class RAGService:
    """
    Retrieval Augmented Generation service.

    Retrieves relevant document chunks based on query similarity.
    """

    def __init__(self, embedding_service=None):
        """
        Initialize RAG service.

        Args:
            embedding_service: Optional EmbeddingService instance
        """
        from .embedding_service import EmbeddingService

        self.embedding_service = embedding_service or EmbeddingService()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.5,
        document_types: Optional[List[str]] = None,
        category_ids: Optional[List[int]] = None,
        team_ids: Optional[List[int]] = None,
        league_ids: Optional[List[int]] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant document chunks for a query.

        Args:
            query: Search query
            top_k: Number of results to return
            min_score: Minimum similarity score (0-1)
            document_types: Filter by document types
            category_ids: Filter by category IDs
            team_ids: Filter by team IDs
            league_ids: Filter by league IDs

        Returns:
            List of RetrievalResult objects
        """
        from apps.documents.models import DocumentChunk

        # Get query embedding
        query_embedding = self.embedding_service.get_embedding(query)

        # Build query
        chunks = DocumentChunk.objects.filter(
            embedding__isnull=False,
            document__is_active=True,
        ).select_related('document')

        # Apply filters
        if document_types:
            chunks = chunks.filter(document__document_type__in=document_types)

        if category_ids:
            chunks = chunks.filter(document__category_id__in=category_ids)

        if team_ids:
            chunks = chunks.filter(document__teams__id__in=team_ids)

        if league_ids:
            chunks = chunks.filter(document__leagues__id__in=league_ids)

        # Calculate cosine distance and order by similarity
        chunks = chunks.annotate(
            distance=CosineDistance('embedding', query_embedding)
        ).filter(
            distance__lt=(1 - min_score)  # Convert score to distance
        ).order_by('distance')[:top_k]

        # Convert to results
        results = []
        for chunk in chunks:
            score = 1 - chunk.distance  # Convert distance back to score
            results.append(RetrievalResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=chunk.document.title,
                content=chunk.content,
                score=score,
                metadata={
                    'document_type': chunk.document.document_type,
                    'chunk_index': chunk.chunk_index,
                    'token_count': chunk.token_count,
                }
            ))

        logger.info(f"Retrieved {len(results)} chunks for query: {query[:50]}...")
        return results

    def retrieve_for_prediction(
        self,
        prediction,
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents for a prediction.

        Builds a comprehensive query from prediction context.

        Args:
            prediction: Prediction model instance
            top_k: Number of results to return

        Returns:
            List of RetrievalResult objects
        """
        match = prediction.match

        # Build contextual query
        query_parts = [
            f"{match.home_team.name} vs {match.away_team.name}",
            f"match prediction analysis",
            f"home win probability {float(prediction.home_win_prob):.0%}",
            f"away win probability {float(prediction.away_win_prob):.0%}",
        ]

        # Add outcome-specific context
        if prediction.predicted_outcome == 'H':
            query_parts.append(f"home team advantage {match.home_team.name}")
        elif prediction.predicted_outcome == 'A':
            query_parts.append(f"away team performance {match.away_team.name}")
        else:
            query_parts.append("draw prediction factors")

        # Add goals context
        if prediction.over_25_prob and float(prediction.over_25_prob) > 0.5:
            query_parts.append("high scoring match analysis")
        else:
            query_parts.append("low scoring defensive match")

        query = " ".join(query_parts)

        # Retrieve with team/league context
        return self.retrieve(
            query=query,
            top_k=top_k,
            min_score=0.3,
            team_ids=[match.home_team_id, match.away_team_id],
        )

    def build_context(
        self,
        results: List[RetrievalResult],
        max_tokens: int = 3000
    ) -> str:
        """
        Build context string from retrieval results.

        Args:
            results: List of retrieval results
            max_tokens: Maximum approximate tokens

        Returns:
            Formatted context string
        """
        if not results:
            return ""

        context_parts = []
        current_tokens = 0

        for result in results:
            # Approximate tokens (words * 1.3)
            chunk_tokens = int(len(result.content.split()) * 1.3)

            if current_tokens + chunk_tokens > max_tokens:
                break

            context_parts.append(
                f"[Source: {result.document_title}]\n{result.content}"
            )
            current_tokens += chunk_tokens

        return "\n\n---\n\n".join(context_parts)

    def get_relevant_stats(
        self,
        home_team_id: int,
        away_team_id: int
    ) -> Dict[str, Any]:
        """
        Get relevant statistics from documents for a matchup.

        Args:
            home_team_id: Home team ID
            away_team_id: Away team ID

        Returns:
            Dict with relevant statistics
        """
        from apps.teams.models import Team, TeamSeasonStats, HeadToHead

        stats = {}

        try:
            home_team = Team.objects.get(id=home_team_id)
            away_team = Team.objects.get(id=away_team_id)

            # Get current season stats
            home_stats = TeamSeasonStats.objects.filter(
                team=home_team,
                season__is_current=True
            ).first()

            away_stats = TeamSeasonStats.objects.filter(
                team=away_team,
                season__is_current=True
            ).first()

            if home_stats:
                played = home_stats.wins + home_stats.draws + home_stats.losses
                stats['home_team'] = {
                    'name': home_team.name,
                    'form': home_stats.form_string[:5] if home_stats.form_string else '',
                    'points': home_stats.wins * 3 + home_stats.draws,
                    'goals_per_game': round(home_stats.goals_for / played, 2) if played else 0,
                    'conceded_per_game': round(home_stats.goals_against / played, 2) if played else 0,
                }

            if away_stats:
                played = away_stats.wins + away_stats.draws + away_stats.losses
                stats['away_team'] = {
                    'name': away_team.name,
                    'form': away_stats.form_string[:5] if away_stats.form_string else '',
                    'points': away_stats.wins * 3 + away_stats.draws,
                    'goals_per_game': round(away_stats.goals_for / played, 2) if played else 0,
                    'conceded_per_game': round(away_stats.goals_against / played, 2) if played else 0,
                }

            # Get H2H
            h2h = HeadToHead.objects.filter(
                Q(team1=home_team, team2=away_team) |
                Q(team1=away_team, team2=home_team)
            ).first()

            if h2h:
                if h2h.team1_id == home_team_id:
                    stats['h2h'] = {
                        'matches': h2h.total_matches,
                        'home_wins': h2h.team1_wins,
                        'away_wins': h2h.team2_wins,
                        'draws': h2h.draws,
                    }
                else:
                    stats['h2h'] = {
                        'matches': h2h.total_matches,
                        'home_wins': h2h.team2_wins,
                        'away_wins': h2h.team1_wins,
                        'draws': h2h.draws,
                    }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")

        return stats
