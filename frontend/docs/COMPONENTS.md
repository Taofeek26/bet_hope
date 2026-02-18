# Bet_Hope Frontend Components

## Component Architecture

Components follow atomic design principles organized into layers.

```
components/
│
├── ui/                    # Base UI (Atoms)
│   ├── Button/
│   ├── Input/
│   ├── Card/
│   ├── Badge/
│   ├── Modal/
│   ├── Table/
│   ├── Tabs/
│   ├── Tooltip/
│   ├── Skeleton/
│   └── Spinner/
│
├── predictions/           # Prediction Components (Molecules)
│   ├── PredictionCard/
│   ├── PredictionList/
│   ├── ProbabilityBar/
│   ├── ConfidenceBadge/
│   ├── OutcomeIndicator/
│   └── KeyFactors/
│
├── matches/               # Match Components (Molecules)
│   ├── MatchCard/
│   ├── MatchList/
│   ├── LiveScore/
│   ├── MatchStats/
│   ├── MatchTimeline/
│   └── H2HHistory/
│
├── leagues/               # League Components (Molecules)
│   ├── LeagueTable/
│   ├── LeagueCard/
│   ├── Fixtures/
│   ├── TopScorers/
│   └── LeagueSelector/
│
├── teams/                 # Team Components (Molecules)
│   ├── TeamCard/
│   ├── TeamBadge/
│   ├── FormIndicator/
│   ├── Squad/
│   └── TeamStats/
│
├── charts/                # Chart Components
│   ├── ProbabilityChart/
│   ├── AccuracyChart/
│   ├── FormChart/
│   ├── PerformanceChart/
│   └── DistributionChart/
│
└── layout/                # Layout Components (Organisms)
    ├── Header/
    ├── Sidebar/
    ├── Footer/
    ├── Navigation/
    ├── PageContainer/
    └── DashboardLayout/
```

---

## UI Components

### Button

Primary action component with multiple variants.

```tsx
// components/ui/Button/Button.tsx
import { cva, type VariantProps } from 'class-variance-authority';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none',
  {
    variants: {
      variant: {
        primary: 'bg-primary-500 text-white hover:bg-primary-600 focus:ring-primary-500',
        secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200 focus:ring-gray-500',
        outline: 'border border-gray-300 bg-transparent hover:bg-gray-50 focus:ring-gray-500',
        ghost: 'bg-transparent hover:bg-gray-100 focus:ring-gray-500',
        danger: 'bg-red-500 text-white hover:bg-red-600 focus:ring-red-500',
        success: 'bg-green-500 text-white hover:bg-green-600 focus:ring-green-500',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-4 text-sm',
        lg: 'h-12 px-6 text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export function Button({
  className,
  variant,
  size,
  isLoading,
  leftIcon,
  rightIcon,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && <Spinner className="mr-2 h-4 w-4" />}
      {!isLoading && leftIcon && <span className="mr-2">{leftIcon}</span>}
      {children}
      {rightIcon && <span className="ml-2">{rightIcon}</span>}
    </button>
  );
}
```

**Usage:**

```tsx
<Button variant="primary" size="lg">
  View Prediction
</Button>

<Button variant="outline" isLoading>
  Loading...
</Button>

<Button variant="ghost" leftIcon={<FilterIcon />}>
  Filter
</Button>
```

---

### Card

Container component for content blocks.

```tsx
// components/ui/Card/Card.tsx
interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
}

export function Card({
  children,
  className,
  padding = 'md',
  hover = false,
}: CardProps) {
  const paddingClasses = {
    none: '',
    sm: 'p-3',
    md: 'p-4 md:p-6',
    lg: 'p-6 md:p-8',
  };

  return (
    <div
      className={cn(
        'bg-white rounded-xl shadow-sm border border-gray-100',
        paddingClasses[padding],
        hover && 'hover:shadow-md transition-shadow cursor-pointer',
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('border-b border-gray-100 pb-4 mb-4', className)}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <h3 className={cn('text-lg font-semibold text-gray-900', className)}>
      {children}
    </h3>
  );
}

export function CardContent({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('', className)}>{children}</div>;
}

export function CardFooter({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('border-t border-gray-100 pt-4 mt-4', className)}>
      {children}
    </div>
  );
}
```

**Usage:**

```tsx
<Card hover>
  <CardHeader>
    <CardTitle>Match Preview</CardTitle>
  </CardHeader>
  <CardContent>
    <p>Match content here...</p>
  </CardContent>
  <CardFooter>
    <Button>View Details</Button>
  </CardFooter>
</Card>
```

---

### Badge

Status indicator component.

```tsx
// components/ui/Badge/Badge.tsx
const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
  {
    variants: {
      variant: {
        default: 'bg-gray-100 text-gray-800',
        primary: 'bg-primary-100 text-primary-800',
        success: 'bg-green-100 text-green-800',
        warning: 'bg-yellow-100 text-yellow-800',
        danger: 'bg-red-100 text-red-800',
        info: 'bg-blue-100 text-blue-800',
      },
      size: {
        sm: 'px-2 py-0.5 text-xs',
        md: 'px-2.5 py-0.5 text-xs',
        lg: 'px-3 py-1 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
);

export function Badge({ variant, size, className, children }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant, size }), className)}>
      {children}
    </span>
  );
}
```

**Usage:**

```tsx
<Badge variant="success">High Confidence</Badge>
<Badge variant="warning">Moderate</Badge>
<Badge variant="danger">Live</Badge>
```

---

### Modal

Dialog component for overlays.

```tsx
// components/ui/Modal/Modal.tsx
'use client';

import { Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
}: ModalProps) {
  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    full: 'max-w-4xl',
  };

  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog onClose={onClose} className="relative z-50">
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
        </Transition.Child>

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel
              className={cn(
                'w-full bg-white rounded-xl shadow-xl',
                sizeClasses[size]
              )}
            >
              {title && (
                <div className="flex items-center justify-between px-6 py-4 border-b">
                  <Dialog.Title className="text-lg font-semibold">
                    {title}
                  </Dialog.Title>
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-500"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>
              )}
              <div className="px-6 py-4">{children}</div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  );
}
```

---

### Table

Data table component.

```tsx
// components/ui/Table/Table.tsx
interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (item: T) => React.ReactNode;
  className?: string;
}

interface TableProps<T> {
  data: T[];
  columns: Column<T>[];
  isLoading?: boolean;
  emptyMessage?: string;
  onRowClick?: (item: T) => void;
}

export function Table<T extends { id: number | string }>({
  data,
  columns,
  isLoading,
  emptyMessage = 'No data available',
  onRowClick,
}: TableProps<T>) {
  if (isLoading) {
    return <TableSkeleton columns={columns.length} rows={5} />;
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200">
            {columns.map((column) => (
              <th
                key={String(column.key)}
                className={cn(
                  'px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider',
                  column.className
                )}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.map((item) => (
            <tr
              key={item.id}
              onClick={() => onRowClick?.(item)}
              className={cn(
                'hover:bg-gray-50 transition-colors',
                onRowClick && 'cursor-pointer'
              )}
            >
              {columns.map((column) => (
                <td
                  key={String(column.key)}
                  className={cn('px-4 py-4 text-sm', column.className)}
                >
                  {column.render
                    ? column.render(item)
                    : String(item[column.key as keyof T] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## Prediction Components

### PredictionCard

Main prediction display component.

```tsx
// components/predictions/PredictionCard/PredictionCard.tsx
interface PredictionCardProps {
  prediction: Prediction;
  showDetails?: boolean;
  onClick?: () => void;
}

export function PredictionCard({
  prediction,
  showDetails = false,
  onClick,
}: PredictionCardProps) {
  const { match } = prediction;
  const recommendedClass = {
    HOME: 'border-l-green-500',
    DRAW: 'border-l-yellow-500',
    AWAY: 'border-l-blue-500',
  };

  return (
    <Card
      hover={!!onClick}
      className={cn('border-l-4', recommendedClass[prediction.recommendedOutcome])}
      onClick={onClick}
    >
      {/* Match Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <LeagueBadge league={match.league} size="sm" />
          <span className="text-xs text-gray-500">
            {formatDate(match.matchDate)} • {match.kickoffTime}
          </span>
        </div>
        <ConfidenceBadge score={prediction.confidence} />
      </div>

      {/* Teams */}
      <div className="flex items-center justify-between mb-4">
        <TeamDisplay team={match.homeTeam} side="home" />
        <div className="text-center px-4">
          <span className="text-xs text-gray-400 uppercase">vs</span>
        </div>
        <TeamDisplay team={match.awayTeam} side="away" />
      </div>

      {/* Probability Bar */}
      <ProbabilityBar
        homeWin={prediction.homeWinProbability * 100}
        draw={prediction.drawProbability * 100}
        awayWin={prediction.awayWinProbability * 100}
      />

      {/* Probability Values */}
      <div className="flex justify-between mt-2 text-sm">
        <span className="text-green-600 font-medium">
          {formatPercent(prediction.homeWinProbability)}
        </span>
        <span className="text-yellow-600 font-medium">
          {formatPercent(prediction.drawProbability)}
        </span>
        <span className="text-blue-600 font-medium">
          {formatPercent(prediction.awayWinProbability)}
        </span>
      </div>

      {/* Key Factors (optional) */}
      {showDetails && prediction.keyFactors.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <KeyFactors factors={prediction.keyFactors} />
        </div>
      )}
    </Card>
  );
}
```

---

### ProbabilityBar

Visual probability distribution.

```tsx
// components/predictions/ProbabilityBar/ProbabilityBar.tsx
interface ProbabilityBarProps {
  homeWin: number;
  draw: number;
  awayWin: number;
  height?: 'sm' | 'md' | 'lg';
  showLabels?: boolean;
}

export function ProbabilityBar({
  homeWin,
  draw,
  awayWin,
  height = 'md',
  showLabels = false,
}: ProbabilityBarProps) {
  const heightClasses = {
    sm: 'h-1.5',
    md: 'h-2.5',
    lg: 'h-4',
  };

  return (
    <div className="w-full">
      <div className={cn('flex rounded-full overflow-hidden', heightClasses[height])}>
        <div
          className="bg-green-500 transition-all duration-500"
          style={{ width: `${homeWin}%` }}
        />
        <div
          className="bg-yellow-400 transition-all duration-500"
          style={{ width: `${draw}%` }}
        />
        <div
          className="bg-blue-500 transition-all duration-500"
          style={{ width: `${awayWin}%` }}
        />
      </div>

      {showLabels && (
        <div className="flex justify-between mt-1 text-xs text-gray-500">
          <span>Home {homeWin.toFixed(0)}%</span>
          <span>Draw {draw.toFixed(0)}%</span>
          <span>Away {awayWin.toFixed(0)}%</span>
        </div>
      )}
    </div>
  );
}
```

---

### ConfidenceBadge

Confidence score indicator.

```tsx
// components/predictions/ConfidenceBadge/ConfidenceBadge.tsx
interface ConfidenceBadgeProps {
  score: number; // 0-1
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function ConfidenceBadge({
  score,
  showLabel = true,
  size = 'md',
}: ConfidenceBadgeProps) {
  const getVariant = (score: number) => {
    if (score >= 0.7) return 'success';
    if (score >= 0.55) return 'warning';
    return 'default';
  };

  const getLabel = (score: number) => {
    if (score >= 0.7) return 'High';
    if (score >= 0.55) return 'Moderate';
    return 'Low';
  };

  return (
    <Badge variant={getVariant(score)} size={size}>
      {showLabel && <span className="mr-1">{getLabel(score)}</span>}
      {(score * 100).toFixed(0)}%
    </Badge>
  );
}
```

---

### KeyFactors

Display prediction reasoning.

```tsx
// components/predictions/KeyFactors/KeyFactors.tsx
interface KeyFactorsProps {
  factors: string[];
  maxDisplay?: number;
}

export function KeyFactors({ factors, maxDisplay = 3 }: KeyFactorsProps) {
  const displayFactors = factors.slice(0, maxDisplay);
  const remaining = factors.length - maxDisplay;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-medium text-gray-500 uppercase">
        Key Factors
      </h4>
      <ul className="space-y-1">
        {displayFactors.map((factor, index) => (
          <li key={index} className="flex items-start gap-2 text-sm text-gray-600">
            <CheckCircleIcon className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
            <span>{factor}</span>
          </li>
        ))}
      </ul>
      {remaining > 0 && (
        <button className="text-xs text-primary-500 hover:underline">
          +{remaining} more factors
        </button>
      )}
    </div>
  );
}
```

---

## Match Components

### MatchCard

Match display with score.

```tsx
// components/matches/MatchCard/MatchCard.tsx
interface MatchCardProps {
  match: Match;
  showPrediction?: boolean;
  onClick?: () => void;
}

export function MatchCard({ match, showPrediction, onClick }: MatchCardProps) {
  const isLive = match.status === 'live';
  const isFinished = match.status === 'finished';

  return (
    <Card hover={!!onClick} onClick={onClick}>
      {/* Status Badge */}
      <div className="flex items-center justify-between mb-3">
        <LeagueBadge league={match.league} size="sm" />
        <MatchStatusBadge status={match.status} minute={match.minute} />
      </div>

      {/* Teams and Score */}
      <div className="flex items-center justify-between">
        {/* Home Team */}
        <div className="flex-1">
          <TeamDisplay team={match.homeTeam} side="home" />
        </div>

        {/* Score / Time */}
        <div className="px-4 text-center min-w-[80px]">
          {isLive || isFinished ? (
            <div className="text-2xl font-bold">
              <span className={match.homeScore > match.awayScore ? 'text-green-600' : ''}>
                {match.homeScore}
              </span>
              <span className="text-gray-300 mx-1">-</span>
              <span className={match.awayScore > match.homeScore ? 'text-green-600' : ''}>
                {match.awayScore}
              </span>
            </div>
          ) : (
            <div className="text-lg font-semibold text-gray-900">
              {match.kickoffTime}
            </div>
          )}
          {!isLive && !isFinished && (
            <div className="text-xs text-gray-500 mt-1">
              {formatDate(match.matchDate, 'short')}
            </div>
          )}
        </div>

        {/* Away Team */}
        <div className="flex-1">
          <TeamDisplay team={match.awayTeam} side="away" />
        </div>
      </div>

      {/* Prediction Preview */}
      {showPrediction && match.prediction && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          <ProbabilityBar
            homeWin={match.prediction.homeWinProbability * 100}
            draw={match.prediction.drawProbability * 100}
            awayWin={match.prediction.awayWinProbability * 100}
            height="sm"
          />
        </div>
      )}
    </Card>
  );
}
```

---

### LiveScore

Real-time score display.

```tsx
// components/matches/LiveScore/LiveScore.tsx
interface LiveScoreProps {
  homeScore: number;
  awayScore: number;
  minute: number;
  isHalfTime?: boolean;
}

export function LiveScore({
  homeScore,
  awayScore,
  minute,
  isHalfTime,
}: LiveScoreProps) {
  return (
    <div className="flex flex-col items-center">
      <div className="flex items-center gap-3">
        <span className="text-3xl font-bold">{homeScore}</span>
        <span className="text-xl text-gray-400">-</span>
        <span className="text-3xl font-bold">{awayScore}</span>
      </div>
      <div className="flex items-center gap-2 mt-2">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
        </span>
        <span className="text-sm font-medium text-red-500">
          {isHalfTime ? 'HT' : `${minute}'`}
        </span>
      </div>
    </div>
  );
}
```

---

## Team Components

### FormIndicator

Team form display (W/D/L).

```tsx
// components/teams/FormIndicator/FormIndicator.tsx
interface FormIndicatorProps {
  form: string; // e.g., "WWDLW"
  size?: 'sm' | 'md' | 'lg';
}

export function FormIndicator({ form, size = 'md' }: FormIndicatorProps) {
  const sizeClasses = {
    sm: 'h-5 w-5 text-xs',
    md: 'h-6 w-6 text-xs',
    lg: 'h-8 w-8 text-sm',
  };

  const resultClasses = {
    W: 'bg-green-500 text-white',
    D: 'bg-yellow-400 text-gray-900',
    L: 'bg-red-500 text-white',
  };

  return (
    <div className="flex gap-1">
      {form.split('').map((result, index) => (
        <span
          key={index}
          className={cn(
            'flex items-center justify-center rounded font-medium',
            sizeClasses[size],
            resultClasses[result as keyof typeof resultClasses]
          )}
        >
          {result}
        </span>
      ))}
    </div>
  );
}
```

---

### TeamBadge

Team logo and name.

```tsx
// components/teams/TeamBadge/TeamBadge.tsx
interface TeamBadgeProps {
  team: Team;
  size?: 'sm' | 'md' | 'lg';
  showName?: boolean;
  reverse?: boolean;
}

export function TeamBadge({
  team,
  size = 'md',
  showName = true,
  reverse = false,
}: TeamBadgeProps) {
  const sizeClasses = {
    sm: 'h-6 w-6',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  return (
    <div
      className={cn(
        'flex items-center gap-2',
        reverse && 'flex-row-reverse'
      )}
    >
      <img
        src={team.logoUrl}
        alt={team.name}
        className={cn('object-contain', sizeClasses[size])}
      />
      {showName && (
        <span className="font-medium text-gray-900">{team.name}</span>
      )}
    </div>
  );
}
```

---

## Chart Components

### ProbabilityChart

Pie/Donut chart for probabilities.

```tsx
// components/charts/ProbabilityChart/ProbabilityChart.tsx
'use client';

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface ProbabilityChartProps {
  homeWin: number;
  draw: number;
  awayWin: number;
  size?: number;
}

const COLORS = {
  home: '#22c55e',   // green
  draw: '#eab308',   // yellow
  away: '#3b82f6',   // blue
};

export function ProbabilityChart({
  homeWin,
  draw,
  awayWin,
  size = 200,
}: ProbabilityChartProps) {
  const data = [
    { name: 'Home Win', value: homeWin, color: COLORS.home },
    { name: 'Draw', value: draw, color: COLORS.draw },
    { name: 'Away Win', value: awayWin, color: COLORS.away },
  ];

  return (
    <div style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={size * 0.3}
            outerRadius={size * 0.4}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) => `${value.toFixed(1)}%`}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

### AccuracyChart

Line chart for model accuracy over time.

```tsx
// components/charts/AccuracyChart/AccuracyChart.tsx
'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface AccuracyChartProps {
  data: Array<{
    date: string;
    accuracy: number;
    predictions: number;
  }>;
  height?: number;
}

export function AccuracyChart({ data, height = 300 }: AccuracyChartProps) {
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => formatDate(value, 'short')}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(1)}%`, 'Accuracy']}
          />
          <Line
            type="monotone"
            dataKey="accuracy"
            stroke="#22c55e"
            strokeWidth={2}
            dot={{ fill: '#22c55e', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

## Layout Components

### DashboardLayout

Main dashboard wrapper.

```tsx
// components/layout/DashboardLayout/DashboardLayout.tsx
interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar */}
      <MobileSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64">
        <Sidebar />
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        <Header onMenuClick={() => setSidebarOpen(true)} />
        <main className="py-6 px-4 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
```

---

## Component Best Practices

### 1. File Structure

```
ComponentName/
├── ComponentName.tsx      # Main component
├── ComponentName.test.tsx # Tests
├── ComponentName.stories.tsx # Storybook (optional)
├── index.ts              # Export
└── types.ts              # Types (if complex)
```

### 2. Props Interface

```tsx
// Always define clear interfaces
interface ComponentProps {
  /** Required: Main data */
  data: DataType;
  /** Optional: Callback on click */
  onClick?: () => void;
  /** Optional: Custom className */
  className?: string;
}
```

### 3. Default Exports

```tsx
// index.ts
export { ComponentName } from './ComponentName';
export type { ComponentNameProps } from './types';
```

### 4. Composition Pattern

```tsx
// Use compound components for flexibility
<Card>
  <Card.Header>Title</Card.Header>
  <Card.Body>Content</Card.Body>
  <Card.Footer>Actions</Card.Footer>
</Card>
```
