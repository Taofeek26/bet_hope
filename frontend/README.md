# Bet_Hope Frontend

## Next.js 14 Web Application

Modern React frontend built with Next.js App Router, TypeScript, and Tailwind CSS.

---

## Project Structure

```
frontend/
│
├── src/
│   ├── app/                     # Next.js App Router
│   │   ├── (auth)/              # Auth routes (login, register)
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── (dashboard)/         # Protected dashboard routes
│   │   │   ├── page.tsx         # Dashboard home
│   │   │   ├── predictions/     # Predictions pages
│   │   │   ├── matches/         # Match pages
│   │   │   ├── leagues/         # League pages
│   │   │   ├── teams/           # Team pages
│   │   │   └── analytics/       # Analytics pages
│   │   ├── layout.tsx           # Root layout
│   │   ├── page.tsx             # Landing page
│   │   └── globals.css          # Global styles
│   │
│   ├── components/              # React components
│   │   ├── ui/                  # Base UI components
│   │   │   ├── Button/
│   │   │   ├── Card/
│   │   │   ├── Modal/
│   │   │   ├── Table/
│   │   │   └── ...
│   │   ├── predictions/         # Prediction components
│   │   │   ├── PredictionCard/
│   │   │   ├── PredictionList/
│   │   │   ├── ConfidenceBadge/
│   │   │   └── ProbabilityBar/
│   │   ├── matches/             # Match components
│   │   │   ├── MatchCard/
│   │   │   ├── MatchList/
│   │   │   ├── LiveScore/
│   │   │   └── MatchStats/
│   │   ├── leagues/             # League components
│   │   │   ├── LeagueTable/
│   │   │   ├── LeagueCard/
│   │   │   └── Fixtures/
│   │   ├── teams/               # Team components
│   │   │   ├── TeamCard/
│   │   │   ├── FormIndicator/
│   │   │   └── Squad/
│   │   ├── charts/              # Chart components
│   │   │   ├── ProbabilityChart/
│   │   │   ├── AccuracyChart/
│   │   │   └── FormChart/
│   │   └── layout/              # Layout components
│   │       ├── Header/
│   │       ├── Sidebar/
│   │       ├── Footer/
│   │       └── Navigation/
│   │
│   ├── hooks/                   # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── usePredictions.ts
│   │   ├── useMatches.ts
│   │   ├── useLeagues.ts
│   │   └── useWebSocket.ts
│   │
│   ├── lib/                     # Utilities & API client
│   │   ├── api/                 # API client
│   │   │   ├── client.ts        # Axios instance
│   │   │   ├── predictions.ts   # Predictions API
│   │   │   ├── matches.ts       # Matches API
│   │   │   ├── leagues.ts       # Leagues API
│   │   │   └── teams.ts         # Teams API
│   │   ├── utils/               # Utility functions
│   │   │   ├── date.ts
│   │   │   ├── format.ts
│   │   │   └── probability.ts
│   │   └── constants.ts         # App constants
│   │
│   ├── stores/                  # State management (Zustand)
│   │   ├── authStore.ts
│   │   ├── predictionsStore.ts
│   │   └── uiStore.ts
│   │
│   └── types/                   # TypeScript types
│       ├── api.ts               # API response types
│       ├── prediction.ts
│       ├── match.ts
│       ├── team.ts
│       └── league.ts
│
├── public/                      # Static assets
│   ├── images/
│   │   ├── logos/               # League & team logos
│   │   └── icons/
│   └── fonts/
│
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
├── Dockerfile
├── .env.example
└── README.md
```

---

## Setup

### Prerequisites

- Node.js 20+
- npm or yarn

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local
# Edit .env.local with your settings

# Run development server
npm run dev

# Open http://localhost:3000
```

### Scripts

```bash
npm run dev          # Development server
npm run build        # Production build
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # TypeScript check
npm run test         # Run tests
```

---

## Pages

### Public Pages

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/login` | User login |
| `/register` | User registration |

### Dashboard Pages (Protected)

| Route | Description |
|-------|-------------|
| `/dashboard` | Main dashboard |
| `/predictions` | All predictions |
| `/predictions/[id]` | Single prediction |
| `/matches` | Match list |
| `/matches/live` | Live matches |
| `/matches/[id]` | Match details |
| `/leagues` | League list |
| `/leagues/[id]` | League standings |
| `/teams` | Team list |
| `/teams/[id]` | Team profile |
| `/analytics` | Model performance |

---

## Components

### UI Components

```tsx
// Button
<Button variant="primary" size="lg">
  View Prediction
</Button>

// Card
<Card>
  <CardHeader>Match Preview</CardHeader>
  <CardContent>...</CardContent>
</Card>

// Badge
<Badge variant="success">High Confidence</Badge>
```

### Prediction Components

```tsx
// Prediction Card
<PredictionCard
  homeTeam="Arsenal"
  awayTeam="Chelsea"
  prediction={{
    homeWin: 0.52,
    draw: 0.25,
    awayWin: 0.23,
    confidence: 0.71
  }}
/>

// Probability Bar
<ProbabilityBar
  homeWin={52}
  draw={25}
  awayWin={23}
/>

// Confidence Badge
<ConfidenceBadge score={0.71} />
```

### Match Components

```tsx
// Match Card
<MatchCard
  match={{
    homeTeam: { name: "Arsenal", logo: "..." },
    awayTeam: { name: "Chelsea", logo: "..." },
    date: "2024-01-15",
    time: "15:00",
    status: "scheduled"
  }}
/>

// Live Score
<LiveScore
  homeScore={2}
  awayScore={1}
  minute={67}
/>
```

### Chart Components

```tsx
// Probability Chart
<ProbabilityChart
  data={[
    { label: "Home", value: 52 },
    { label: "Draw", value: 25 },
    { label: "Away", value: 23 }
  ]}
/>

// Accuracy Chart
<AccuracyChart
  data={weeklyAccuracy}
  period="30d"
/>
```

---

## API Client

### Configuration

```typescript
// lib/api/client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### API Functions

```typescript
// lib/api/predictions.ts
export const predictionsApi = {
  getUpcoming: () => apiClient.get('/predictions/upcoming/'),
  getById: (id: number) => apiClient.get(`/predictions/match/${id}/`),
  getByLeague: (leagueId: number) => apiClient.get(`/predictions/league/${leagueId}/`),
  getToday: () => apiClient.get('/predictions/today/'),
};

// lib/api/matches.ts
export const matchesApi = {
  getAll: (params?: MatchParams) => apiClient.get('/matches/', { params }),
  getById: (id: number) => apiClient.get(`/matches/${id}/`),
  getLive: () => apiClient.get('/matches/live/'),
};
```

---

## Hooks

### usePredictions

```typescript
import { useQuery } from '@tanstack/react-query';
import { predictionsApi } from '@/lib/api/predictions';

export function usePredictions() {
  return useQuery({
    queryKey: ['predictions', 'upcoming'],
    queryFn: () => predictionsApi.getUpcoming(),
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  });
}

// Usage
const { data, isLoading, error } = usePredictions();
```

### useAuth

```typescript
export function useAuth() {
  const { user, token, login, logout } = useAuthStore();

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: (data) => {
      login(data.user, data.token);
    },
  });

  return {
    user,
    isAuthenticated: !!token,
    login: loginMutation.mutate,
    logout,
    isLoading: loginMutation.isPending,
  };
}
```

### useWebSocket

```typescript
export function useWebSocket(channel: string) {
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/${channel}/`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages((prev) => [...prev, data]);
    };

    return () => ws.close();
  }, [channel]);

  return messages;
}
```

---

## State Management

### Zustand Stores

```typescript
// stores/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  user: User | null;
  token: string | null;
  login: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      login: (user, token) => set({ user, token }),
      logout: () => set({ user: null, token: null }),
    }),
    { name: 'auth-storage' }
  )
);
```

---

## TypeScript Types

```typescript
// types/prediction.ts
export interface Prediction {
  id: number;
  match: Match;
  homeWinProbability: number;
  drawProbability: number;
  awayWinProbability: number;
  confidence: number;
  recommendedOutcome: 'HOME' | 'DRAW' | 'AWAY';
  keyFactors: string[];
  modelVersion: string;
  createdAt: string;
}

// types/match.ts
export interface Match {
  id: number;
  homeTeam: Team;
  awayTeam: Team;
  league: League;
  matchDate: string;
  kickoffTime: string;
  status: MatchStatus;
  homeScore?: number;
  awayScore?: number;
  venue?: string;
  matchweek?: number;
}

export type MatchStatus =
  | 'scheduled'
  | 'live'
  | 'halftime'
  | 'finished'
  | 'postponed';
```

---

## Styling

### Tailwind Configuration

```typescript
// tailwind.config.ts
export default {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0fdf4',
          500: '#22c55e',
          600: '#16a34a',
        },
        accent: {
          500: '#3b82f6',
        },
      },
    },
  },
  plugins: [],
};
```

### Global Styles

```css
/* app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .btn-primary {
    @apply bg-primary-500 text-white px-4 py-2 rounded-lg hover:bg-primary-600;
  }

  .card {
    @apply bg-white rounded-xl shadow-md p-6;
  }

  .badge-success {
    @apply bg-green-100 text-green-800 px-2 py-1 rounded-full text-sm;
  }
}
```

---

## Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_APP_NAME=Bet_Hope
```

---

## Docker

### Build

```bash
docker build -t bet-hope-frontend .
```

### Run

```bash
docker run -p 3000:3000 bet-hope-frontend
```

---

## Testing

```bash
# Run tests
npm run test

# Run tests with coverage
npm run test:coverage

# Run e2e tests
npm run test:e2e
```

---

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Docker

```bash
docker build -t bet-hope-frontend .
docker run -p 3000:3000 bet-hope-frontend
```

---

## Best Practices

1. **Component Structure**: Use atomic design (atoms → molecules → organisms)
2. **Data Fetching**: Use React Query for server state
3. **State Management**: Use Zustand for client state
4. **Type Safety**: Use TypeScript strictly
5. **Error Handling**: Use error boundaries
6. **Loading States**: Always show loading indicators
7. **Responsive Design**: Mobile-first approach
