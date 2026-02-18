'use client';

import { useQuery } from '@tanstack/react-query';
import { TrendingUp, Filter, Calendar, RefreshCw } from 'lucide-react';
import { predictionsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useState } from 'react';

export default function PredictionsPage() {
  const [filter, setFilter] = useState('all');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['predictions', filter],
    queryFn: () => predictionsApi.getUpcoming(),
  });

  const predictions = data?.predictions || [];

  return (
    <>
      <div className="content-header">
        <h1>Predictions</h1>
        <p>AI-powered match predictions with confidence scores</p>
      </div>

      {/* Filters */}
      <div className="card card-compact mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-text-muted" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="input select w-40"
            >
              <option value="all">All Matches</option>
              <option value="high">High Confidence</option>
              <option value="today">Today Only</option>
              <option value="value">Value Bets</option>
            </select>
          </div>
          <button onClick={() => refetch()} className="btn btn-secondary btn-sm">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Predictions List */}
      {isLoading ? (
        <div className="flex justify-center py-20">
          <LoadingSpinner />
        </div>
      ) : error ? (
        <div className="card text-center py-12">
          <p className="text-text-muted mb-4">Failed to load predictions</p>
          <button onClick={() => refetch()} className="btn btn-primary">
            Try Again
          </button>
        </div>
      ) : predictions.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-3">
          {predictions.map((prediction: any) => (
            <PredictionCard key={prediction.id} prediction={prediction} />
          ))}
        </div>
      )}
    </>
  );
}

function PredictionCard({ prediction }: { prediction: any }) {
  const probs = prediction.probabilities || {};
  const homeProb = probs.home || 0.33;
  const drawProb = probs.draw || 0.33;
  const awayProb = probs.away || 0.34;
  const confidence = parseFloat(prediction.confidence_score) || 0;
  const match = prediction.match || {};

  return (
    <div className="card card-compact">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="card-icon w-10 h-10">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <div className="font-semibold text-text">
              {match.home_team || 'Home'} vs {match.away_team || 'Away'}
            </div>
            <div className="text-xs text-text-muted flex items-center gap-2">
              <Calendar className="w-3 h-3" />
              {match.match_date || 'TBD'} {match.kickoff_time && `• ${match.kickoff_time}`}
              {match.league && <span className="text-text-sec">• {match.league}</span>}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-sm font-semibold text-brand">
            {(confidence * 100).toFixed(0)}% confidence
          </div>
          <div className="text-xs text-text-muted">
            Predicted: {prediction.recommended_outcome || 'HOME'}
          </div>
        </div>
      </div>

      {/* Probability Bars */}
      <div className="grid grid-cols-3 gap-4">
        <ProbabilityItem label="Home" value={homeProb} />
        <ProbabilityItem label="Draw" value={drawProb} />
        <ProbabilityItem label="Away" value={awayProb} />
      </div>
    </div>
  );
}

function ProbabilityItem({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-text-muted">{label}</span>
        <span className="text-text-sec">{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="probability-bar">
        <div
          className="probability-fill"
          style={{ width: `${value * 100}%` }}
        />
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="card text-center py-16">
      <div className="card-icon w-16 h-16 mx-auto mb-4">
        <TrendingUp className="w-8 h-8" />
      </div>
      <h3 className="text-lg font-semibold text-text mb-2">No Predictions Available</h3>
      <p className="text-text-muted text-sm max-w-sm mx-auto">
        Predictions will appear here once the backend is connected and data is available.
      </p>
    </div>
  );
}
