"""
API URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    LeagueViewSet,
    SeasonViewSet,
    TeamViewSet,
    MatchViewSet,
    PredictionViewSet,
)
from .views.ai_recommendations import AIRecommendationViewSet, DocumentViewSet

# Create router
router = DefaultRouter()
router.register(r'leagues', LeagueViewSet, basename='league')
router.register(r'seasons', SeasonViewSet, basename='season')
router.register(r'teams', TeamViewSet, basename='team')
router.register(r'matches', MatchViewSet, basename='match')
router.register(r'predictions', PredictionViewSet, basename='prediction')
router.register(r'ai-recommendations', AIRecommendationViewSet, basename='ai-recommendation')
router.register(r'documents', DocumentViewSet, basename='document')

app_name = 'api'

urlpatterns = [
    path('', include(router.urls)),
]
