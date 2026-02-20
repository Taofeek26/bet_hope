'use client';

import { useQuery } from '@tanstack/react-query';
import { TrendingUp, Filter, Calendar, RefreshCw, CheckCircle, Clock, XCircle, Check, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { predictionsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { AIEnhancement } from '@/components/predictions/AIEnhancement';
import { useState, useMemo } from 'react';

// Date utilities
function formatDateForAPI(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function formatDateDisplay(date: Date, today: Date): string {
  const diffDays = Math.floor((date.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Tomorrow';
  if (diffDays === -1) return 'Yesterday';
  return `${dayNames[date.getDay()]} ${date.getDate()} ${monthNames[date.getMonth()]}`;
}

export default function PredictionsPage() {
  const [filter, setFilter] = useState('all');
  const [selectedDateOffset, setSelectedDateOffset] = useState(0);

  // Calculate dates
  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  const selectedDate = useMemo(() => {
    const d = new Date(today);
    d.setDate(d.getDate() + selectedDateOffset);
    return d;
  }, [today, selectedDateOffset]);

  const selectedDateStr = formatDateForAPI(selectedDate);
  const selectedDateLabel = formatDateDisplay(selectedDate, today);

  // Generate date options (3 days back + today + 6 days forward)
  const dateOptions = useMemo(() => {
    return Array.from({ length: 10 }, (_, i) => {
      const offset = i - 3; // -3 to +6
      const d = new Date(today);
      d.setDate(d.getDate() + offset);
      return {
        offset,
        date: d,
        label: formatDateDisplay(d, today),
        short: offset === 0 ? 'Today' : offset === 1 ? 'Tom' : offset === -1 ? 'Yest' : `${d.getDate()}`,
      };
    });
  }, [today]);

  // Fetch predictions based on selected date
  const { data, isLoading, error, refetch } = useQuery<any>({
    queryKey: ['predictions', selectedDateStr, filter],
    queryFn: () => predictionsApi.getAll({
      date_from: selectedDateStr,
      date_to: selectedDateStr,
      min_confidence: filter === 'high' ? 0.7 : undefined,
    }),
  });

  // Filter predictions based on dropdown
  const predictions = useMemo(() => {
    let results = data || [];

    if (filter === 'high') {
      results = results.filter((p: any) => parseFloat(p.confidence_score) >= 0.7);
    } else if (filter === 'value') {
      results = results.filter((p: any) => p.is_value_bet === true);
    }

    return results;
  }, [data, filter]);

  return (
    <>
      <div className="content-header">
        <h1>Predictions</h1>
        <p>AI-powered match predictions with confidence scores</p>
      </div>

      {/* Date Selector & Filters */}
      <div className="card card-compact mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          {/* Date Selector */}
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-text-muted" />
            <button
              onClick={() => setSelectedDateOffset(selectedDateOffset - 1)}
              disabled={selectedDateOffset <= -3}
              className="btn btn-secondary btn-sm p-1 disabled:opacity-50"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <div className="flex gap-1">
              {dateOptions.slice(Math.max(0, selectedDateOffset + 3 - 3), Math.max(0, selectedDateOffset + 3 - 3) + 7).map((opt) => (
                <button
                  key={opt.offset}
                  onClick={() => setSelectedDateOffset(opt.offset)}
                  className={`px-2 sm:px-3 py-1.5 text-[10px] sm:text-xs font-medium rounded-lg transition-all ${
                    selectedDateOffset === opt.offset
                      ? 'bg-brand text-bg'
                      : 'bg-surface text-text-muted hover:bg-input hover:text-text'
                  }`}
                >
                  {opt.short}
                </button>
              ))}
            </div>

            <button
              onClick={() => setSelectedDateOffset(selectedDateOffset + 1)}
              disabled={selectedDateOffset >= 6}
              className="btn btn-secondary btn-sm p-1 disabled:opacity-50"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Filter Dropdown */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-text-muted" />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="input select w-40"
              >
                <option value="all">All Matches</option>
                <option value="high">High Confidence</option>
                <option value="value">Value Bets</option>
              </select>
            </div>
            <button onClick={() => refetch()} className="btn btn-secondary btn-sm">
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Selected Date Label */}
        <div className="mt-3 pt-3 border-t border-border-dim">
          <p className="text-sm text-text-muted">
            Showing predictions for <span className="text-text font-medium">{selectedDateLabel}</span>
            {predictions.length > 0 && (
              <span className="ml-2 text-text-sec">({predictions.length} matches)</span>
            )}
          </p>
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
  const isFinished = match.status === 'finished';
  const verification = prediction.result_verification;
  const hasVerification = verification && verification.actual_score;
  const isCorrect = verification?.is_correct;

  return (
    <div className={`card card-compact ${isFinished ? hasVerification ? (isCorrect ? 'border-l-4 border-l-green-500' : 'border-l-4 border-l-red-500') : 'border-l-4 border-l-text-muted/30' : ''}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`card-icon w-10 h-10 ${isFinished ? (hasVerification ? (isCorrect ? 'bg-green-500/20' : 'bg-red-500/20') : 'bg-surface-alt') : ''}`}>
            {isFinished ? (
              hasVerification ? (
                isCorrect ? <Check className="w-5 h-5 text-green-500" /> : <X className="w-5 h-5 text-red-500" />
              ) : <CheckCircle className="w-5 h-5 text-text-muted" />
            ) : <TrendingUp className="w-5 h-5" />}
          </div>
          <div>
            <div className="font-semibold text-text flex items-center gap-2">
              <div className="flex items-center gap-1.5">
                {match.home_team_logo ? (
                  <img src={match.home_team_logo} alt={match.home_team} className="w-5 h-5 object-contain" />
                ) : (
                  <div className="w-5 h-5 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand">
                    {(match.home_team || 'H')?.charAt(0)}
                  </div>
                )}
                <span>{match.home_team || 'Home'}</span>
              </div>
              <span className="text-text-muted text-sm">vs</span>
              <div className="flex items-center gap-1.5">
                <span>{match.away_team || 'Away'}</span>
                {match.away_team_logo ? (
                  <img src={match.away_team_logo} alt={match.away_team} className="w-5 h-5 object-contain" />
                ) : (
                  <div className="w-5 h-5 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand">
                    {(match.away_team || 'A')?.charAt(0)}
                  </div>
                )}
              </div>
              {hasVerification && (
                <span className={`text-xs px-2 py-0.5 rounded font-medium ${isCorrect ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
                  FT: {verification.actual_score}
                </span>
              )}
            </div>
            <div className="text-xs text-text-muted flex items-center gap-2">
              {isFinished ? <CheckCircle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
              {match.match_date || 'TBD'} {match.kickoff_time && `• ${match.kickoff_time}`}
              {match.league && <span className="text-text-sec">• {match.league}</span>}
              {isFinished && <span className="text-text-sec">• Finished</span>}
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

      {/* Result Verification for Finished Matches */}
      {hasVerification && (
        <div className={`mb-4 p-3 rounded-lg ${isCorrect ? 'bg-green-500/10 border border-green-500/20' : 'bg-red-500/10 border border-red-500/20'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isCorrect ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <XCircle className="w-5 h-5 text-red-500" />
              )}
              <span className={`text-sm font-medium ${isCorrect ? 'text-green-500' : 'text-red-500'}`}>
                {isCorrect ? 'Prediction Correct!' : 'Prediction Incorrect'}
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <div>
                <span className="text-text-muted">Predicted: </span>
                <span className="font-medium text-text">{verification.predicted_result}</span>
                {verification.predicted_score && (
                  <span className="text-text-muted ml-1">({verification.predicted_score})</span>
                )}
              </div>
              <div>
                <span className="text-text-muted">Actual: </span>
                <span className="font-medium text-text">{verification.actual_result}</span>
                <span className="text-text-muted ml-1">({verification.actual_score})</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Probability Bars */}
      <div className="grid grid-cols-3 gap-4">
        <ProbabilityItem label="Home" value={homeProb} isActual={hasVerification && verification.actual_result === 'HOME'} />
        <ProbabilityItem label="Draw" value={drawProb} isActual={hasVerification && verification.actual_result === 'DRAW'} />
        <ProbabilityItem label="Away" value={awayProb} isActual={hasVerification && verification.actual_result === 'AWAY'} />
      </div>

      {/* AI Enhancement - only show for non-finished matches */}
      {prediction.id && !isFinished && (
        <AIEnhancement
          predictionId={prediction.id}
          matchInfo={{
            homeTeam: match.home_team || 'Home',
            awayTeam: match.away_team || 'Away',
          }}
        />
      )}
    </div>
  );
}

function ProbabilityItem({ label, value, isActual }: { label: string; value: number; isActual?: boolean }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className={isActual ? 'text-green-500 font-medium' : 'text-text-muted'}>
          {label} {isActual && '✓'}
        </span>
        <span className={isActual ? 'text-green-500 font-medium' : 'text-text-sec'}>{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="probability-bar">
        <div
          className={`probability-fill ${isActual ? '!bg-green-500' : ''}`}
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
