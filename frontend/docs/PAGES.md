# Bet_Hope Pages & Routing

## Overview

Uses Next.js 14 App Router with route groups and layouts.

---

## Route Structure

```
src/app/
│
├── (marketing)/              # Public marketing pages
│   ├── page.tsx             # Landing page (/)
│   ├── about/
│   │   └── page.tsx         # About page (/about)
│   ├── pricing/
│   │   └── page.tsx         # Pricing page (/pricing)
│   └── layout.tsx           # Marketing layout
│
├── (auth)/                   # Authentication pages
│   ├── login/
│   │   └── page.tsx         # Login (/login)
│   ├── register/
│   │   └── page.tsx         # Register (/register)
│   ├── forgot-password/
│   │   └── page.tsx         # Forgot password (/forgot-password)
│   ├── reset-password/
│   │   └── page.tsx         # Reset password (/reset-password)
│   └── layout.tsx           # Auth layout (centered card)
│
├── (dashboard)/              # Protected dashboard pages
│   ├── dashboard/
│   │   └── page.tsx         # Dashboard home (/dashboard)
│   ├── predictions/
│   │   ├── page.tsx         # All predictions (/predictions)
│   │   └── [id]/
│   │       └── page.tsx     # Single prediction (/predictions/123)
│   ├── matches/
│   │   ├── page.tsx         # Match list (/matches)
│   │   ├── live/
│   │   │   └── page.tsx     # Live matches (/matches/live)
│   │   └── [id]/
│   │       └── page.tsx     # Match details (/matches/123)
│   ├── leagues/
│   │   ├── page.tsx         # All leagues (/leagues)
│   │   └── [id]/
│   │       ├── page.tsx     # League details (/leagues/1)
│   │       ├── standings/
│   │       │   └── page.tsx # Standings (/leagues/1/standings)
│   │       └── fixtures/
│   │           └── page.tsx # Fixtures (/leagues/1/fixtures)
│   ├── teams/
│   │   ├── page.tsx         # All teams (/teams)
│   │   └── [id]/
│   │       └── page.tsx     # Team details (/teams/123)
│   ├── analytics/
│   │   └── page.tsx         # Model analytics (/analytics)
│   ├── settings/
│   │   └── page.tsx         # User settings (/settings)
│   └── layout.tsx           # Dashboard layout (sidebar + header)
│
├── api/                      # API routes (if needed)
│   └── auth/
│       └── [...nextauth]/
│           └── route.ts
│
├── layout.tsx                # Root layout
├── loading.tsx               # Global loading
├── error.tsx                 # Global error
├── not-found.tsx             # 404 page
└── globals.css               # Global styles
```

---

## Page Implementations

### Landing Page

```tsx
// app/(marketing)/page.tsx
import { HeroSection } from '@/components/marketing/HeroSection';
import { FeaturesSection } from '@/components/marketing/FeaturesSection';
import { PredictionsPreview } from '@/components/marketing/PredictionsPreview';
import { CTASection } from '@/components/marketing/CTASection';

export const metadata = {
  title: 'Bet_Hope - AI Football Predictions',
  description: 'AI-powered football match predictions with confidence scores.',
};

export default function LandingPage() {
  return (
    <>
      <HeroSection />
      <FeaturesSection />
      <PredictionsPreview />
      <CTASection />
    </>
  );
}
```

---

### Login Page

```tsx
// app/(auth)/login/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/stores/authStore';
import { authApi } from '@/lib/api/auth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await authApi.login({ email, password });
      login(response.user, response.access, response.refresh);
      router.push('/dashboard');
    } catch (err) {
      setError('Invalid email or password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md">
      <h1 className="text-2xl font-bold text-center mb-8">
        Sign in to Bet_Hope
      </h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <Input
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <div className="flex items-center justify-between text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" className="rounded" />
            Remember me
          </label>
          <Link href="/forgot-password" className="text-primary-500 hover:underline">
            Forgot password?
          </Link>
        </div>

        <Button type="submit" className="w-full" isLoading={isLoading}>
          Sign in
        </Button>

        <p className="text-center text-sm text-gray-500">
          Don't have an account?{' '}
          <Link href="/register" className="text-primary-500 hover:underline">
            Sign up
          </Link>
        </p>
      </form>
    </div>
  );
}
```

---

### Dashboard Page

```tsx
// app/(dashboard)/dashboard/page.tsx
import { Suspense } from 'react';
import { TodayPredictions } from '@/components/dashboard/TodayPredictions';
import { LiveMatches } from '@/components/dashboard/LiveMatches';
import { QuickStats } from '@/components/dashboard/QuickStats';
import { RecentResults } from '@/components/dashboard/RecentResults';
import { ModelPerformance } from '@/components/dashboard/ModelPerformance';
import { Skeleton } from '@/components/ui/Skeleton';

export const metadata = {
  title: 'Dashboard | Bet_Hope',
};

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Overview of today's predictions and live matches</p>
      </div>

      {/* Quick Stats */}
      <Suspense fallback={<Skeleton className="h-24" />}>
        <QuickStats />
      </Suspense>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Today's Predictions */}
        <div className="lg:col-span-2">
          <Suspense fallback={<Skeleton className="h-96" />}>
            <TodayPredictions />
          </Suspense>
        </div>

        {/* Live Matches */}
        <div>
          <Suspense fallback={<Skeleton className="h-96" />}>
            <LiveMatches />
          </Suspense>
        </div>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Results */}
        <Suspense fallback={<Skeleton className="h-64" />}>
          <RecentResults />
        </Suspense>

        {/* Model Performance */}
        <Suspense fallback={<Skeleton className="h-64" />}>
          <ModelPerformance />
        </Suspense>
      </div>
    </div>
  );
}
```

---

### Predictions List Page

```tsx
// app/(dashboard)/predictions/page.tsx
'use client';

import { useState } from 'react';
import { useUpcomingPredictions } from '@/hooks/usePredictions';
import { useLeagues } from '@/hooks/useLeagues';
import { PredictionCard } from '@/components/predictions/PredictionCard';
import { FilterBar } from '@/components/predictions/FilterBar';
import { Skeleton } from '@/components/ui/Skeleton';
import { Empty } from '@/components/ui/Empty';

export default function PredictionsPage() {
  const [filters, setFilters] = useState({
    leagueId: null as number | null,
    minConfidence: 0,
    date: null as string | null,
  });

  const { data: predictions, isLoading, error } = useUpcomingPredictions();
  const { data: leagues } = useLeagues();

  // Filter predictions
  const filteredPredictions = predictions?.filter((p) => {
    if (filters.leagueId && p.match.league.id !== filters.leagueId) return false;
    if (filters.minConfidence && p.confidence < filters.minConfidence) return false;
    if (filters.date && p.match.matchDate !== filters.date) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Predictions</h1>
          <p className="text-gray-500">
            AI-powered predictions for upcoming matches
          </p>
        </div>
      </div>

      {/* Filters */}
      <FilterBar
        leagues={leagues || []}
        filters={filters}
        onFilterChange={setFilters}
      />

      {/* Content */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-64" />
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-12 text-red-500">
          Failed to load predictions
        </div>
      ) : filteredPredictions?.length === 0 ? (
        <Empty
          title="No predictions found"
          description="Try adjusting your filters or check back later"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPredictions?.map((prediction) => (
            <PredictionCard
              key={prediction.id}
              prediction={prediction}
              onClick={() => {/* navigate to detail */}}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

---

### Prediction Detail Page

```tsx
// app/(dashboard)/predictions/[id]/page.tsx
import { notFound } from 'next/navigation';
import { predictionsApi } from '@/lib/api/predictions';
import { PredictionDetail } from '@/components/predictions/PredictionDetail';
import { MatchInfo } from '@/components/matches/MatchInfo';
import { H2HHistory } from '@/components/matches/H2HHistory';
import { TeamComparison } from '@/components/predictions/TeamComparison';

interface Props {
  params: { id: string };
}

export async function generateMetadata({ params }: Props) {
  const prediction = await predictionsApi.getByMatch(Number(params.id));
  return {
    title: `${prediction.match.homeTeam.name} vs ${prediction.match.awayTeam.name} | Bet_Hope`,
  };
}

export default async function PredictionDetailPage({ params }: Props) {
  const prediction = await predictionsApi.getByMatch(Number(params.id));

  if (!prediction) {
    notFound();
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <BackButton href="/predictions" />

      {/* Match Info */}
      <MatchInfo match={prediction.match} />

      {/* Prediction Card */}
      <PredictionDetail prediction={prediction} />

      {/* Team Comparison */}
      <TeamComparison
        homeTeam={prediction.match.homeTeam}
        awayTeam={prediction.match.awayTeam}
      />

      {/* Head to Head */}
      <H2HHistory
        teamA={prediction.match.homeTeam}
        teamB={prediction.match.awayTeam}
      />
    </div>
  );
}
```

---

### Live Matches Page

```tsx
// app/(dashboard)/matches/live/page.tsx
'use client';

import { useLiveMatches } from '@/hooks/useMatches';
import { useLiveUpdates } from '@/hooks/useWebSocket';
import { LiveMatchCard } from '@/components/matches/LiveMatchCard';
import { Empty } from '@/components/ui/Empty';

export default function LiveMatchesPage() {
  const { data: matches, isLoading } = useLiveMatches();

  // Enable real-time updates
  useLiveUpdates();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="relative flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500" />
        </span>
        <h1 className="text-2xl font-bold text-gray-900">Live Matches</h1>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : matches?.length === 0 ? (
        <Empty
          title="No live matches"
          description="Check back when matches are in progress"
          icon={<CalendarIcon className="h-12 w-12 text-gray-400" />}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {matches?.map((match) => (
            <LiveMatchCard key={match.id} match={match} />
          ))}
        </div>
      )}
    </div>
  );
}
```

---

### League Standings Page

```tsx
// app/(dashboard)/leagues/[id]/standings/page.tsx
import { leaguesApi } from '@/lib/api/leagues';
import { LeagueHeader } from '@/components/leagues/LeagueHeader';
import { StandingsTable } from '@/components/leagues/StandingsTable';
import { SeasonSelector } from '@/components/leagues/SeasonSelector';

interface Props {
  params: { id: string };
  searchParams: { season?: string };
}

export default async function LeagueStandingsPage({
  params,
  searchParams,
}: Props) {
  const leagueId = Number(params.id);
  const season = searchParams.season || 'current';

  const [league, standings] = await Promise.all([
    leaguesApi.getById(leagueId),
    leaguesApi.getStandings(leagueId, season),
  ]);

  return (
    <div className="space-y-6">
      {/* League Header */}
      <LeagueHeader league={league} activeTab="standings" />

      {/* Season Selector */}
      <div className="flex justify-end">
        <SeasonSelector currentSeason={season} leagueId={leagueId} />
      </div>

      {/* Standings Table */}
      <StandingsTable standings={standings} />
    </div>
  );
}
```

---

### Team Detail Page

```tsx
// app/(dashboard)/teams/[id]/page.tsx
import { Suspense } from 'react';
import { teamsApi } from '@/lib/api/teams';
import { TeamHeader } from '@/components/teams/TeamHeader';
import { TeamStats } from '@/components/teams/TeamStats';
import { RecentMatches } from '@/components/teams/RecentMatches';
import { UpcomingFixtures } from '@/components/teams/UpcomingFixtures';
import { Squad } from '@/components/teams/Squad';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';

interface Props {
  params: { id: string };
}

export default async function TeamDetailPage({ params }: Props) {
  const teamId = Number(params.id);
  const team = await teamsApi.getById(teamId);

  return (
    <div className="space-y-6">
      {/* Team Header */}
      <TeamHeader team={team} />

      {/* Stats Overview */}
      <TeamStats team={team} />

      {/* Tabbed Content */}
      <Tabs defaultValue="matches">
        <TabsList>
          <TabsTrigger value="matches">Matches</TabsTrigger>
          <TabsTrigger value="fixtures">Fixtures</TabsTrigger>
          <TabsTrigger value="squad">Squad</TabsTrigger>
        </TabsList>

        <TabsContent value="matches">
          <Suspense fallback={<Skeleton className="h-64" />}>
            <RecentMatches teamId={teamId} />
          </Suspense>
        </TabsContent>

        <TabsContent value="fixtures">
          <Suspense fallback={<Skeleton className="h-64" />}>
            <UpcomingFixtures teamId={teamId} />
          </Suspense>
        </TabsContent>

        <TabsContent value="squad">
          <Suspense fallback={<Skeleton className="h-64" />}>
            <Squad teamId={teamId} />
          </Suspense>
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

---

### Analytics Page

```tsx
// app/(dashboard)/analytics/page.tsx
'use client';

import { useState } from 'react';
import { useModelPerformance } from '@/hooks/useAnalytics';
import { AccuracyChart } from '@/components/charts/AccuracyChart';
import { PerformanceByLeague } from '@/components/analytics/PerformanceByLeague';
import { ConfidenceDistribution } from '@/components/analytics/ConfidenceDistribution';
import { PeriodSelector } from '@/components/analytics/PeriodSelector';
import { StatsGrid } from '@/components/analytics/StatsGrid';

export default function AnalyticsPage() {
  const [period, setPeriod] = useState('30d');
  const { data: performance, isLoading } = useModelPerformance(period);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Model Analytics</h1>
          <p className="text-gray-500">Track prediction accuracy and performance</p>
        </div>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      {/* Stats Grid */}
      <StatsGrid
        accuracy={performance?.overall.accuracy}
        totalPredictions={performance?.overall.totalPredictions}
        correctPredictions={performance?.overall.correctPredictions}
        isLoading={isLoading}
      />

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Accuracy Over Time */}
        <Card>
          <CardHeader>
            <CardTitle>Accuracy Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            <AccuracyChart data={performance?.trend || []} />
          </CardContent>
        </Card>

        {/* By League */}
        <Card>
          <CardHeader>
            <CardTitle>Performance by League</CardTitle>
          </CardHeader>
          <CardContent>
            <PerformanceByLeague data={performance?.byLeague || []} />
          </CardContent>
        </Card>

        {/* By Confidence */}
        <Card>
          <CardHeader>
            <CardTitle>Accuracy by Confidence Level</CardTitle>
          </CardHeader>
          <CardContent>
            <ConfidenceDistribution data={performance?.byConfidence} />
          </CardContent>
        </Card>

        {/* By Outcome */}
        <Card>
          <CardHeader>
            <CardTitle>Accuracy by Outcome</CardTitle>
          </CardHeader>
          <CardContent>
            <OutcomeAccuracy data={performance?.byOutcome} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

---

## Layouts

### Root Layout

```tsx
// app/layout.tsx
import { Inter } from 'next/font/google';
import { Providers } from './providers';
import { Toaster } from '@/components/ui/Toaster';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'Bet_Hope - AI Football Predictions',
  description: 'AI-powered football match predictions',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
```

---

### Dashboard Layout

```tsx
// app/(dashboard)/layout.tsx
import { redirect } from 'next/navigation';
import { getServerSession } from '@/lib/auth';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

export default async function Layout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession();

  if (!session) {
    redirect('/login');
  }

  return <DashboardLayout>{children}</DashboardLayout>;
}
```

---

### Auth Layout

```tsx
// app/(auth)/layout.tsx
import Link from 'next/link';
import Image from 'next/image';

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary-500 items-center justify-center p-12">
        <div className="text-white text-center">
          <h1 className="text-4xl font-bold mb-4">Bet_Hope</h1>
          <p className="text-xl text-primary-100">
            AI-Powered Football Predictions
          </p>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Logo for mobile */}
          <div className="lg:hidden text-center mb-8">
            <Link href="/">
              <Image src="/logo.svg" alt="Bet_Hope" width={120} height={40} />
            </Link>
          </div>

          {children}
        </div>
      </div>
    </div>
  );
}
```

---

## Error Handling

### Error Boundary

```tsx
// app/error.tsx
'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/Button';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log to error reporting service
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Something went wrong
        </h1>
        <p className="text-gray-500 mb-8">
          We're sorry, an unexpected error occurred.
        </p>
        <Button onClick={reset}>Try again</Button>
      </div>
    </div>
  );
}
```

---

### Not Found

```tsx
// app/not-found.tsx
import Link from 'next/link';
import { Button } from '@/components/ui/Button';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-900 mb-4">404</h1>
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">
          Page Not Found
        </h2>
        <p className="text-gray-500 mb-8">
          The page you're looking for doesn't exist.
        </p>
        <Link href="/dashboard">
          <Button>Go to Dashboard</Button>
        </Link>
      </div>
    </div>
  );
}
```

---

### Loading States

```tsx
// app/(dashboard)/predictions/loading.tsx
import { Skeleton } from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-10 w-48" />
      <Skeleton className="h-12 w-full" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <Skeleton key={i} className="h-64" />
        ))}
      </div>
    </div>
  );
}
```

---

## Middleware

```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const protectedRoutes = ['/dashboard', '/predictions', '/matches', '/leagues', '/teams', '/analytics', '/settings'];
const authRoutes = ['/login', '/register', '/forgot-password'];

export function middleware(request: NextRequest) {
  const token = request.cookies.get('token')?.value;
  const { pathname } = request.nextUrl;

  // Redirect authenticated users away from auth pages
  if (authRoutes.some((route) => pathname.startsWith(route))) {
    if (token) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }
  }

  // Redirect unauthenticated users to login
  if (protectedRoutes.some((route) => pathname.startsWith(route))) {
    if (!token) {
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
```
