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

// Format odds — decimal is the raw stored value; fractional/american are
// derived from it. Settings > Region & Odds > Odds Format controls which.
export type OddsFormat = 'decimal' | 'fractional' | 'american';

export function formatOdds(odds: number | null | undefined, format: OddsFormat = 'decimal') {
  if (!odds || odds <= 1) return '-';

  if (format === 'american') {
    const american = odds >= 2 ? (odds - 1) * 100 : -100 / (odds - 1);
    return american > 0 ? `+${Math.round(american)}` : `${Math.round(american)}`;
  }

  if (format === 'fractional') {
    const decimalPart = odds - 1;
    // Approximate as a fraction with a denominator up to 100 — good enough
    // for display; betting fractional odds are conventionally simplified,
    // but exact simplification isn't worth the complexity here.
    let bestNum = 1;
    let bestDen = 1;
    let bestErr = Infinity;
    for (let den = 1; den <= 100; den++) {
      const num = Math.round(decimalPart * den);
      if (num < 1) continue;
      const err = Math.abs(num / den - decimalPart);
      if (err < bestErr) {
        bestErr = err;
        bestNum = num;
        bestDen = den;
        if (err < 0.001) break;
      }
    }
    const gcd = (a: number, b: number): number => (b === 0 ? a : gcd(b, a % b));
    const g = gcd(bestNum, bestDen);
    return `${bestNum / g}/${bestDen / g}`;
  }

  return odds.toFixed(2);
}

// Date format — Settings > Region & Odds > Date Format.
export type DateFormatPreset = 'DD/MM/YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD';

const DATE_FORMAT_PATTERNS: Record<DateFormatPreset, string> = {
  'DD/MM/YYYY': 'dd/MM/yyyy',
  'MM/DD/YYYY': 'MM/dd/yyyy',
  'YYYY-MM-DD': 'yyyy-MM-dd',
};

export function formatDateWithPreset(date: string | Date, preset: DateFormatPreset) {
  const d = typeof date === 'string' ? parseISO(date) : date;
  return format(d, DATE_FORMAT_PATTERNS[preset]);
}

// Timezone-aware time formatting — Settings > Region & Odds > Timezone.
// 'local' uses the browser's own zone (Intl default); anything else is an
// explicit IANA zone name.
export function formatTimeInZone(date: string | Date, timezone: string) {
  const d = typeof date === 'string' ? parseISO(date) : date;
  try {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: timezone === 'local' ? undefined : timezone,
    }).format(d);
  } catch {
    return formatTime(typeof date === 'string' ? date : date.toISOString());
  }
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
