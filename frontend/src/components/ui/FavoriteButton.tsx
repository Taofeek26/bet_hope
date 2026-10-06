'use client';

import { useEffect, useState } from 'react';
import { Star } from 'lucide-react';
import { useFavoritesStore } from '@/lib/store';

/**
 * Star toggle for a team or league (Phase 4). Favourites are kept in this
 * browser (zustand persist, key "bet-hope-favorites"); there are no user
 * accounts. Before this, no page had a way to add a favourite.
 */
export function FavoriteButton({ kind, id, label }: { kind: 'team' | 'league'; id: number | string; label: string }) {
  const { favoriteTeams, favoriteLeagues, toggleFavoriteTeam, toggleFavoriteLeague } = useFavoritesStore();
  // Persisted state loads after the first render; avoid a server/client mismatch.
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);

  const active = ready && (kind === 'team'
    ? favoriteTeams.includes(id as number)
    : favoriteLeagues.includes(id as string));
  const toggle = () => (kind === 'team' ? toggleFavoriteTeam(id as number) : toggleFavoriteLeague(id as string));

  return (
    <button
      onClick={toggle}
      aria-pressed={active}
      aria-label={active ? `Remove ${label} from favourites` : `Add ${label} to favourites`}
      title={active ? 'Remove from favourites' : 'Add to favourites'}
      className={`btn btn-sm ${active ? 'btn-primary' : 'btn-secondary'}`}
    >
      <Star className={`w-4 h-4 ${active ? 'fill-current' : ''}`} />
      {active ? 'Favourite' : 'Add to favourites'}
    </button>
  );
}
