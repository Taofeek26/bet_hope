'use client';

import { Suspense, useState, useMemo } from 'react';
import {
  TrendingUp,
  Target,
  Percent,
  Zap,
  Calendar,
  Trophy,
  ArrowUpRight,
  ArrowDownRight,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { DailyPicks } from '@/components/predictions/DailyPicks';
import { UpcomingMatches } from '@/components/matches/UpcomingMatches';
import { LiveMatches } from '@/components/matches/LiveMatches';
import { PredictionStats } from '@/components/predictions/PredictionStats';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useDailyPicks, useLiveMatches, useValueBets, usePredictionStats, useWeeklyAvailability } from '@/hooks/useApi';

// Date utilities
function formatDateForAPI(date: Date): string {
  // Use local date parts to avoid timezone shifts
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

function DashboardStats() {
  const { data: dailyPicks } = useDailyPicks();
  const { data: liveMatches } = useLiveMatches();
  const { data: valueBets } = useValueBets();
  const { data: stats } = usePredictionStats({ days: 30 });

  const accuracy = stats?.accuracy ? `${(stats.accuracy * 100).toFixed(1)}%` : '--';
  const predictionsToday = dailyPicks?.total_picks ?? '--';
  const liveCount = liveMatches?.count ?? 0;
  const valueBetsCount = valueBets?.total ?? '--';

  return (
    <div className="stats-grid">
      <StatCard value={accuracy} label="Accuracy Rate" />
      <StatCard value={String(predictionsToday)} label="Predictions Today" />
      <StatCard value={String(liveCount)} label="Live Matches" />
      <StatCard value={String(valueBetsCount)} label="Value Bets" />
    </div>
  );
}

export default function HomePage() {
  const [selectedDateOffset, setSelectedDateOffset] = useState(0);
  const { data: weeklyAvailability } = useWeeklyAvailability();

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

  // Generate date options (today + 6 days) with availability data
  const dateOptions = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(today);
      d.setDate(d.getDate() + i);
      const availability = weeklyAvailability?.days?.find(day => day.day_offset === i);
      return {
        offset: i,
        date: d,
        label: formatDateDisplay(d, today),
        short: i === 0 ? 'Today' : i === 1 ? 'Tom' : `${d.getDate()}`,
        matchCount: availability?.high_confidence ?? 0,
        hasMatches: (availability?.high_confidence ?? 0) > 0,
      };
    });
  }, [today, weeklyAvailability]);

  return (
    <>
      {/* Content Header */}
      <div className="content-header">
        <h1>Dashboard</h1>
        <p>AI-powered predictions across 20 major leagues worldwide</p>
      </div>

      {/* Stats Grid */}
      <DashboardStats />

      {/* Main Content Grid */}
      <div className="content-grid">
        {/* Live Matches - Full Width */}
        <div className="col-span-12">
          <Suspense fallback={<LoadingSection />}>
            <LiveMatches />
          </Suspense>
        </div>

        {/* Daily Picks - 8 columns */}
        <div className="col-span-8">
          <div className="card">
            <div className="card-header flex-wrap gap-4">
              <div className="flex items-center gap-3">
                <div className="card-icon">
                  <Target className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="card-title">
                    {selectedDateOffset === 0 ? "Today's Top Picks" : `Picks for ${selectedDateLabel}`}
                  </h2>
                  <p className="card-desc">High confidence predictions</p>
                </div>
              </div>

              {/* Date Selector */}
              <div className="flex items-center gap-2 ml-auto">
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
                      className={`relative px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                        selectedDateOffset === opt.offset
                          ? 'bg-brand text-bg'
                          : opt.hasMatches
                          ? 'bg-surface text-text-muted hover:bg-input hover:text-text'
                          : 'bg-surface/50 text-text-muted/50'
                      }`}
                    >
                      {opt.short}
                      {opt.hasMatches && (
                        <span className={`absolute -top-1 -right-1 w-4 h-4 text-[10px] rounded-full flex items-center justify-center ${
                          selectedDateOffset === opt.offset
                            ? 'bg-bg text-brand'
                            : 'bg-brand text-bg'
                        }`}>
                          {opt.matchCount}
                        </span>
                      )}
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
            </div>
            <Suspense fallback={<LoadingSection />}>
              <DailyPicks date={selectedDateStr} />
            </Suspense>
          </div>
        </div>

        {/* Sidebar Stats - 4 columns */}
        <div className="col-span-4">
          <div className="card">
            <div className="card-header">
              <div className="card-icon">
                <Percent className="w-5 h-5" />
              </div>
              <div>
                <h2 className="card-title">Model Performance</h2>
                <p className="card-desc">Last 30 days accuracy</p>
              </div>
            </div>
            <Suspense fallback={<LoadingSection />}>
              <PredictionStats />
            </Suspense>
          </div>

          {/* Quick Actions Card */}
          <div className="card">
            <div className="card-header">
              <div className="card-icon">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h2 className="card-title">Quick Actions</h2>
              </div>
            </div>
            <div className="space-y-2">
              <QuickAction
                icon={TrendingUp}
                label="View All Predictions"
                href="/predictions"
              />
              <QuickAction
                icon={Target}
                label="Value Bets"
                href="/value-bets"
              />
              <QuickAction
                icon={Trophy}
                label="League Standings"
                href="/leagues"
              />
              <QuickAction
                icon={Calendar}
                label="Match Schedule"
                href="/matches"
              />
            </div>
          </div>
        </div>

        {/* Upcoming Matches - Full Width */}
        <div className="col-span-12">
          <div className="card">
            <div className="card-header">
              <div className="card-icon">
                <Calendar className="w-5 h-5" />
              </div>
              <div>
                <h2 className="card-title">Upcoming Matches</h2>
                <p className="card-desc">Next 7 days fixtures with predictions</p>
              </div>
            </div>
            <Suspense fallback={<LoadingSection />}>
              <UpcomingMatches />
            </Suspense>
          </div>
        </div>
      </div>
    </>
  );
}

// Stat Card Component
interface StatCardProps {
  value: string;
  label: string;
  change?: string;
  positive?: boolean;
  badge?: string;
}

function StatCard({ value, label, change, positive, badge }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {change && (
        <div className={`stat-change ${positive ? 'positive' : 'negative'}`}>
          {positive ? (
            <ArrowUpRight className="w-3 h-3 inline mr-1" />
          ) : (
            <ArrowDownRight className="w-3 h-3 inline mr-1" />
          )}
          {change}
        </div>
      )}
      {badge && (
        <div className="badge badge-live mt-2">{badge}</div>
      )}
    </div>
  );
}

// Quick Action Component
interface QuickActionProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  href: string;
  badge?: string;
}

function QuickAction({ icon: Icon, label, href, badge }: QuickActionProps) {
  return (
    <a
      href={href}
      className="flex items-center gap-3 p-3 rounded-lg bg-surface border border-border-dim hover:border-border hover:bg-input transition-all group"
    >
      <Icon className="w-4 h-4 text-brand" />
      <span className="flex-1 text-sm text-text-sec group-hover:text-text">{label}</span>
      {badge && (
        <span className="badge badge-brand">{badge}</span>
      )}
    </a>
  );
}

// Loading Section Component
function LoadingSection() {
  return (
    <div className="flex items-center justify-center py-12">
      <LoadingSpinner />
    </div>
  );
}
