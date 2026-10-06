'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Search, X } from 'lucide-react';
import { teamsApi } from '@/lib/api';
import { Logo } from '@/components/ui/Logo';
import { TaskStatusIndicator } from '@/components/ui/TaskStatusIndicator';

/**
 * Phase 4: the search box now searches teams (it had no handler), and the
 * menu, bell (with a permanent fake "unread" dot) and user buttons, which
 * did nothing, are gone. The sidebar has its own collapse control.
 */
export function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 bg-background-secondary/80 backdrop-blur-sm border-b border-border/50 mb-6">
      <div className="flex items-center justify-between h-16 px-4 gap-4">
        <Link href="/" className="flex-shrink-0" aria-label="Bet Hope home">
          <Logo />
        </Link>

        <div className="flex-1 max-w-xl hidden md:block">
          <TeamSearch />
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-2 rounded-lg hover:bg-surface text-text-secondary"
            aria-label={mobileOpen ? 'Close search' : 'Search teams'}
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Search className="w-5 h-5" />}
          </button>
          <TaskStatusIndicator />
        </div>
      </div>

      {mobileOpen && (
        <div className="md:hidden px-4 pb-4">
          <TeamSearch autoFocus onPick={() => setMobileOpen(false)} />
        </div>
      )}
    </header>
  );
}

function TeamSearch({ autoFocus = false, onPick }: { autoFocus?: boolean; onPick?: () => void }) {
  const router = useRouter();
  const [text, setText] = useState('');
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const boxRef = useRef<HTMLDivElement>(null);

  // Debounce: search 250 ms after typing stops, from 2 characters
  useEffect(() => {
    const t = setTimeout(() => setQuery(text.trim()), 250);
    return () => clearTimeout(t);
  }, [text]);

  const { data: teams = [], isFetching } = useQuery({
    queryKey: ['team-search', query],
    queryFn: () => teamsApi.getAll({ search: query }),
    enabled: query.length >= 2,
    staleTime: 60_000,
  });
  const results = teams.slice(0, 8);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const go = (id: number) => {
    setOpen(false);
    setText('');
    onPick?.();
    router.push(`/teams/${id}`);
  };

  return (
    <div className="relative" ref={boxRef}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary" aria-hidden="true" />
      <input
        type="search"
        value={text}
        autoFocus={autoFocus}
        onChange={(e) => { setText(e.target.value); setOpen(true); setActive(0); }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, results.length - 1)); }
          if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
          if (e.key === 'Enter' && results[active]) go(results[active].id);
          if (e.key === 'Escape') setOpen(false);
        }}
        placeholder="Search teams..."
        aria-label="Search teams"
        role="combobox"
        aria-expanded={open && query.length >= 2}
        aria-controls="team-search-results"
        className="w-full pl-10 pr-4 py-2 rounded-lg bg-surface border border-border text-text placeholder:text-text-muted focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
      />
      {open && query.length >= 2 && (
        <ul
          id="team-search-results"
          role="listbox"
          className="absolute left-0 right-0 top-full mt-2 bg-card border border-border rounded-xl shadow-2xl overflow-hidden z-50"
        >
          {results.length === 0 ? (
            <li className="px-4 py-3 text-sm text-text-muted">
              {isFetching ? 'Searching...' : `No teams match "${query}"`}
            </li>
          ) : (
            results.map((t, i) => (
              <li key={t.id} role="option" aria-selected={i === active}>
                <button
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => go(t.id)}
                  onMouseEnter={() => setActive(i)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 text-left ${i === active ? 'bg-surface' : ''}`}
                >
                  {t.logo_url ? (
                    <img src={t.logo_url} alt="" className="w-5 h-5 object-contain" />
                  ) : (
                    <span className="w-5 h-5 rounded-full bg-brand/10 text-brand text-[10px] font-bold flex items-center justify-center">
                      {t.name.charAt(0)}
                    </span>
                  )}
                  <span className="text-sm text-text flex-1 truncate">{t.name}</span>
                  <span className="text-xs text-text-muted">{t.league_name}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
