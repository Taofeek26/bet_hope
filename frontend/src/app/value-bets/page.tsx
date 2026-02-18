'use client';

import { useQuery } from '@tanstack/react-query';
import { Target, TrendingUp, AlertCircle, Clock, RefreshCw } from 'lucide-react';
import { predictionsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export default function ValueBetsPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['value-bets'],
    queryFn: () => predictionsApi.getValueBets(),
  });

  const valueBets = data?.value_bets || [];

  return (
    <>
      <div className="content-header">
        <h1>Value Bets</h1>
        <p>High-value betting opportunities identified by our AI</p>
      </div>

      {/* Info Card */}
      <div className="card card-compact mb-6 border-brand/30">
        <div className="flex items-start gap-4">
          <div className="card-icon bg-brand/10">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-text mb-1">What are Value Bets?</h3>
            <p className="text-sm text-text-sec">
              Value bets occur when our model calculates a higher probability than what the bookmaker odds imply.
              An edge of 5%+ indicates potential value.
            </p>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid mb-6">
        <div className="stat-card">
          <div className="stat-value">{valueBets.length}</div>
          <div className="stat-label">Active Value Bets</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {valueBets.length > 0
              ? `${(valueBets.filter((b: any) => b.rating === 'strong').length / valueBets.length * 100).toFixed(0)}%`
              : '--'}
          </div>
          <div className="stat-label">Strong Bets</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {valueBets.length > 0
              ? `${(valueBets.reduce((sum: number, b: any) => sum + (b.edge || 0), 0) / valueBets.length * 100).toFixed(1)}%`
              : '--'}
          </div>
          <div className="stat-label">Avg Edge</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {valueBets.length > 0
              ? (valueBets.reduce((sum: number, b: any) => sum + (b.odds || 0), 0) / valueBets.length).toFixed(2)
              : '--'}
          </div>
          <div className="stat-label">Avg Odds</div>
        </div>
      </div>

      <div className="flex justify-end mb-4">
        <button onClick={() => refetch()} className="btn btn-secondary btn-sm">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <LoadingSpinner />
        </div>
      ) : error ? (
        <div className="card text-center py-12">
          <p className="text-text-muted mb-4">Failed to load value bets</p>
          <button onClick={() => refetch()} className="btn btn-primary">
            Try Again
          </button>
        </div>
      ) : valueBets.length === 0 ? (
        <div className="card text-center py-16">
          <div className="card-icon w-16 h-16 mx-auto mb-4">
            <Target className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-semibold text-text mb-2">No Value Bets Available</h3>
          <p className="text-text-muted text-sm max-w-sm mx-auto">
            Value bets will appear here once the backend is connected and predictions are generated.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {valueBets.map((bet: any) => (
            <ValueBetCard key={bet.id} bet={bet} />
          ))}
        </div>
      )}
    </>
  );
}

function ValueBetCard({ bet }: { bet: any }) {
  const edge = bet.edge || 0;
  const isStrong = bet.rating === 'strong' || edge > 0.1;
  const isModerate = !isStrong && edge > 0.05;
  const match = bet.match || {};

  // Map market to readable label
  const marketLabel = bet.market === 'home' ? 'Home Win' : bet.market === 'away' ? 'Away Win' : 'Draw';

  // Determine card styling based on strength - using brand color palette only
  const cardClass = isStrong
    ? 'border-2 border-brand bg-brand/5'
    : isModerate
    ? 'border border-brand/40 bg-brand/[0.02]'
    : 'border border-border';

  const badgeClass = isStrong
    ? 'bg-brand text-bg font-bold'
    : isModerate
    ? 'bg-brand/70 text-bg'
    : 'badge-outline';

  const iconBgClass = isStrong
    ? 'bg-brand/20 text-brand'
    : isModerate
    ? 'bg-brand/10 text-brand/70'
    : 'bg-surface text-text-muted';

  return (
    <div className={`card card-compact ${cardClass} transition-all hover:scale-[1.01]`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`card-icon ${iconBgClass}`}>
            <Target className="w-5 h-5" />
          </div>
          <div>
            <div className="font-semibold text-text">
              {match.home_team || 'Home'} vs {match.away_team || 'Away'}
            </div>
            <div className="text-xs text-text-muted flex items-center gap-2">
              <Clock className="w-3 h-3" />
              {match.date || 'TBD'} {match.time && `• ${match.time}`}
            </div>
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full text-xs font-semibold ${badgeClass}`}>
          {isStrong ? 'STRONG VALUE' : isModerate ? 'GOOD VALUE' : 'VALUE BET'}
        </div>
      </div>

      <div className={`grid grid-cols-4 gap-4 p-4 rounded-lg ${isStrong ? 'bg-brand/10' : isModerate ? 'bg-brand/5' : 'bg-surface'}`}>
        <div className="text-center">
          <div className="text-xs text-text-muted mb-1">Bet Type</div>
          <div className="font-semibold text-text">{marketLabel}</div>
        </div>
        <div className="text-center">
          <div className="text-xs text-text-muted mb-1">Model Prob</div>
          <div className={`font-semibold ${isStrong ? 'text-brand' : isModerate ? 'text-brand/80' : 'text-text'}`}>
            {((bet.model_probability || 0) * 100).toFixed(1)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-text-muted mb-1">Market Odds</div>
          <div className="font-semibold text-text">{(bet.odds || 0).toFixed(2)}</div>
        </div>
        <div className="text-center">
          <div className="text-xs text-text-muted mb-1">Edge</div>
          <div className={`font-bold text-lg ${isStrong ? 'text-brand' : isModerate ? 'text-brand/80' : 'text-text-sec'}`}>
            +{(edge * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Confidence indicator bar */}
      <div className="mt-3 h-1 rounded-full bg-surface overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${isStrong ? 'bg-brand' : isModerate ? 'bg-brand/60' : 'bg-text-muted'}`}
          style={{ width: `${Math.min(edge * 500, 100)}%` }}
        />
      </div>
    </div>
  );
}

