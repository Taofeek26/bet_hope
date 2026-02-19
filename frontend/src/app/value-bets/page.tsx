'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Target, TrendingUp, AlertCircle, Clock, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';
import { predictionsApi } from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

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
  return `${dayNames[date.getDay()]} ${date.getDate()} ${monthNames[date.getMonth()]}`;
}

export default function ValueBetsPage() {
  const [selectedDateOffset, setSelectedDateOffset] = useState(0);
  const [viewMode, setViewMode] = useState<'day' | 'week'>('day');

  // Calculate the selected date based on offset
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

  // Generate date options (today + 6 days)
  const dateOptions = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(today);
      d.setDate(d.getDate() + i);
      return {
        offset: i,
        date: d,
        label: formatDateDisplay(d, today),
        short: i === 0 ? 'Today' : i === 1 ? 'Tom' : `${d.getDate()}`,
      };
    });
  }, [today]);

  // Fetch value bets - either for specific date or all week
  const { data, isLoading, error, refetch } = useQuery<any>({
    queryKey: ['value-bets', viewMode === 'day' ? selectedDateStr : 'week'],
    queryFn: () => predictionsApi.getValueBets(
      viewMode === 'day' ? { date: selectedDateStr } : { days: 7 }
    ),
  });

  const valueBets = data?.value_bets || [];

  // Filter by date if in week view and a date is selected
  const filteredBets = useMemo(() => {
    if (viewMode === 'week') return valueBets;
    return valueBets.filter((bet: any) => bet.match?.date === selectedDateStr);
  }, [valueBets, selectedDateStr, viewMode]);

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

      {/* Date Selector Card */}
      <div className="card card-compact mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className="card-icon">
              <Target className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-semibold text-text">
                {viewMode === 'day'
                  ? (selectedDateOffset === 0 ? "Today's Value Bets" : `Value Bets for ${selectedDateLabel}`)
                  : "All Value Bets (Next 7 Days)"
                }
              </h2>
              <p className="text-xs text-text-muted">
                {filteredBets.length} value bet{filteredBets.length !== 1 ? 's' : ''} found
              </p>
            </div>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1 bg-surface rounded-lg p-1">
              <button
                onClick={() => setViewMode('day')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  viewMode === 'day'
                    ? 'bg-brand text-bg'
                    : 'text-text-muted hover:text-text'
                }`}
              >
                By Day
              </button>
              <button
                onClick={() => setViewMode('week')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                  viewMode === 'week'
                    ? 'bg-brand text-bg'
                    : 'text-text-muted hover:text-text'
                }`}
              >
                All Week
              </button>
            </div>

            {/* Date Navigation (only in day mode) */}
            {viewMode === 'day' && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedDateOffset(Math.max(0, selectedDateOffset - 1))}
                  disabled={selectedDateOffset === 0}
                  className="btn btn-secondary btn-sm p-1 disabled:opacity-50"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                <div className="flex gap-1">
                  {dateOptions.map((opt) => (
                    <button
                      key={opt.offset}
                      onClick={() => setSelectedDateOffset(opt.offset)}
                      className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
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
                  onClick={() => setSelectedDateOffset(Math.min(6, selectedDateOffset + 1))}
                  disabled={selectedDateOffset === 6}
                  className="btn btn-secondary btn-sm p-1 disabled:opacity-50"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}

            <button onClick={() => refetch()} className="btn btn-secondary btn-sm">
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid mb-6">
        <div className="stat-card">
          <div className="stat-value">{filteredBets.length}</div>
          <div className="stat-label">Active Value Bets</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {filteredBets.length > 0
              ? `${(filteredBets.filter((b: any) => b.rating === 'strong').length / filteredBets.length * 100).toFixed(0)}%`
              : '--'}
          </div>
          <div className="stat-label">Strong Bets</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {filteredBets.length > 0
              ? `${(filteredBets.reduce((sum: number, b: any) => sum + (b.edge || 0), 0) / filteredBets.length * 100).toFixed(1)}%`
              : '--'}
          </div>
          <div className="stat-label">Avg Edge</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {filteredBets.length > 0
              ? (filteredBets.reduce((sum: number, b: any) => sum + (b.odds || 0), 0) / filteredBets.length).toFixed(2)
              : '--'}
          </div>
          <div className="stat-label">Avg Odds</div>
        </div>
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
      ) : filteredBets.length === 0 ? (
        <div className="card text-center py-16">
          <div className="card-icon w-16 h-16 mx-auto mb-4">
            <Target className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-semibold text-text mb-2">
            No Value Bets for {viewMode === 'day' ? selectedDateLabel : 'This Week'}
          </h3>
          <p className="text-text-muted text-sm max-w-sm mx-auto">
            {viewMode === 'day'
              ? 'Try selecting a different date or view all week.'
              : 'Value bets will appear here when our model identifies opportunities with positive edge.'}
          </p>
          {viewMode === 'day' && (
            <button
              onClick={() => setViewMode('week')}
              className="btn btn-secondary mt-4"
            >
              View All Week
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredBets.map((bet: any, index: number) => (
            <ValueBetCard key={`${bet.match?.id}-${bet.market}-${index}`} bet={bet} />
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

  // Format date for display
  const matchDate = match.date ? new Date(match.date) : null;
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const dateLabel = matchDate
    ? `${dayNames[matchDate.getDay()]} ${matchDate.getDate()}/${matchDate.getMonth() + 1}`
    : 'TBD';

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
            <div className="font-semibold text-text flex items-center gap-2">
              <div className="flex items-center gap-1.5">
                {match.home_team_logo ? (
                  <img src={match.home_team_logo} alt={match.home_team} className="w-5 h-5 object-contain" />
                ) : (
                  <div className="w-5 h-5 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand">
                    {match.home_team?.charAt(0) || 'H'}
                  </div>
                )}
                <span>{match.home_team || 'Home'}</span>
              </div>
              <span className="text-text-muted">vs</span>
              <div className="flex items-center gap-1.5">
                <span>{match.away_team || 'Away'}</span>
                {match.away_team_logo ? (
                  <img src={match.away_team_logo} alt={match.away_team} className="w-5 h-5 object-contain" />
                ) : (
                  <div className="w-5 h-5 rounded-full bg-brand/10 flex items-center justify-center text-xs font-bold text-brand">
                    {match.away_team?.charAt(0) || 'A'}
                  </div>
                )}
              </div>
            </div>
            <div className="text-xs text-text-muted flex items-center gap-2">
              <Clock className="w-3 h-3" />
              {dateLabel} {match.time && `• ${match.time}`}
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
