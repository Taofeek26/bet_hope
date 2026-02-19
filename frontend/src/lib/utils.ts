import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, formatDistanceToNow, parseISO, isToday, isTomorrow } from 'date-fns';

// Merge Tailwind classes
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Format date for display
export function formatDate(date: string | Date, formatStr: string = 'MMM d, yyyy') {
  const d = typeof date === 'string' ? parseISO(date) : date;
  return format(d, formatStr);
}

// Format date relative to now
export function formatRelativeDate(date: string | Date) {
  const d = typeof date === 'string' ? parseISO(date) : date;

  if (isToday(d)) {
    return 'Today';
  }
  if (isTomorrow(d)) {
    return 'Tomorrow';
  }

  return formatDistanceToNow(d, { addSuffix: true });
}

// Format time
export function formatTime(time: string | null | undefined) {
  if (!time) return '';
  // Handle HH:MM:SS format
  const parts = time.split(':');
  if (parts.length >= 2) {
    return `${parts[0]}:${parts[1]}`;
  }
  return time;
}

// Format probability as percentage
export function formatProbability(prob: number, decimals: number = 0) {
  return `${(prob * 100).toFixed(decimals)}%`;
}

// Format odds
export function formatOdds(odds: number | null | undefined) {
  if (!odds) return '-';
  return odds.toFixed(2);
}

// Get result color class
export function getResultColor(result: 'W' | 'D' | 'L' | string) {
  switch (result) {
    case 'W':
    case 'H':
      return 'text-green-400';
    case 'D':
      return 'text-yellow-400';
    case 'L':
    case 'A':
      return 'text-red-400';
    default:
      return 'text-slate-400';
  }
}

// Get result background class
export function getResultBgColor(result: 'W' | 'D' | 'L' | string) {
  switch (result) {
    case 'W':
    case 'H':
      return 'bg-green-500/20';
    case 'D':
      return 'bg-yellow-500/20';
    case 'L':
    case 'A':
      return 'bg-red-500/20';
    default:
      return 'bg-slate-500/20';
  }
}

// Get confidence color
export function getConfidenceColor(confidence: number) {
  if (confidence >= 0.6) return 'text-green-400';
  if (confidence >= 0.45) return 'text-yellow-400';
  return 'text-red-400';
}

// Get confidence label
export function getConfidenceLabel(confidence: number) {
  if (confidence >= 0.6) return 'High';
  if (confidence >= 0.45) return 'Medium';
  return 'Low';
}

// Parse form string into array
export function parseFormString(form: string | undefined): ('W' | 'D' | 'L')[] {
  if (!form) return [];
  return form.split('') as ('W' | 'D' | 'L')[];
}

// Calculate implied probability from odds
export function oddsToProb(odds: number): number {
  if (odds <= 1) return 0;
  return 1 / odds;
}

// Calculate edge (model prob - market prob)
export function calculateEdge(modelProb: number, marketOdds: number): number {
  const impliedProb = oddsToProb(marketOdds);
  return modelProb - impliedProb;
}

// Get outcome label
export function getOutcomeLabel(outcome: 'H' | 'D' | 'A' | string) {
  switch (outcome) {
    case 'H':
      return 'Home Win';
    case 'D':
      return 'Draw';
    case 'A':
      return 'Away Win';
    default:
      return outcome;
  }
}

// Truncate text
export function truncate(str: string, length: number) {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

// Group matches by date
export function groupMatchesByDate<T extends { match_date: string }>(
  matches: T[]
): Record<string, T[]> {
  return matches.reduce((acc, match) => {
    const date = match.match_date;
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(match);
    return acc;
  }, {} as Record<string, T[]>);
}

// Sort by confidence descending
export function sortByConfidence<T extends { confidence: number }>(items: T[]): T[] {
  return [...items].sort((a, b) => b.confidence - a.confidence);
}
