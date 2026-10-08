'use client';

import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Gamepad2, Trophy } from 'lucide-react';
import api from '@/lib/api';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ShareButton } from '@/components/engage/ShareButton';

const TOKEN_KEY = 'bethope_game_token';
const getToken = () => { try { return localStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; } };

/**
 * Score challenge (Phase 6): predict the exact score of the week's big
 * matches, beat the other players and the Bet Hope model. For fun only:
 * no stakes, no prizes.
 */
export default function GamePage() {
  const qc = useQueryClient();
  const [token, setToken] = useState('');
  const [week, setWeek] = useState(0);
  useEffect(() => setToken(getToken()), []);
  const { data, isLoading } = useQuery({
    queryKey: ['game-week', week, token],
    queryFn: async () => (await api.get('/engage/game_week/', { params: { week }, headers: token ? { 'X-Game-Token': token } : {} })).data,
  });

  return (
    <>
      <div className="content-header">
        <h1>Score challenge</h1>
        <p>Predict the exact score of this week&apos;s big matches. Exact score = 3 points, right result = 1. Can you beat the model? For fun only: no stakes, no prizes.</p>
      </div>

      {!token && <JoinCard onJoined={(t) => { setToken(t); qc.invalidateQueries({ queryKey: ['game-week'] }); }} />}

      <div className="flex items-center gap-2 mb-4">
        {[0, -1].map((w) => (
          <button key={w} onClick={() => setWeek(w)} className={`btn btn-sm ${week === w ? 'btn-primary' : 'btn-secondary'}`}>
            {w === 0 ? 'This week' : 'Last week'}
          </button>
        ))}
        {data && <span className="text-xs text-text-muted ml-auto">{data.week_start} – {data.week_end}</span>}
      </div>

      {isLoading || !data ? <LoadingSpinner /> : (
        <div className="content-grid">
          <div className="col-span-8">
            <div className="card">
              <div className="card-header">
                <div className="card-icon"><Gamepad2 className="w-5 h-5" /></div>
                <div>
                  <h2 className="card-title">Matches</h2>
                  <p className="card-desc">Top 5 leagues and the Champions League · picks close at kickoff</p>
                </div>
              </div>
              {!data.matches.length ? <p className="text-sm text-text-muted py-6 text-center">No big matches this week (international break?).</p> : (
                <ul className="divide-y divide-border-dim">
                  {data.matches.map((m: any) => <MatchRow key={m.id} m={m} token={token} onSaved={() => qc.invalidateQueries({ queryKey: ['game-week'] })} />)}
                </ul>
              )}
            </div>
          </div>
          <div className="col-span-4">
            <div className="card">
              <div className="card-header">
                <div className="card-icon"><Trophy className="w-5 h-5" /></div>
                <div>
                  <h2 className="card-title">Leaderboard</h2>
                  <p className="card-desc">Points from finished matches</p>
                </div>
              </div>
              <ol className="space-y-1">
                {data.leaderboard.map((r: any) => (
                  <li key={r.name} className={`flex items-center justify-between gap-2 p-2 rounded-lg text-sm ${r.name === data.player ? 'bg-brand/10 border border-brand/30' : r.is_model ? 'bg-surface' : ''}`}>
                    <span className="min-w-0 truncate"><span className="text-text-muted w-6 inline-block">{r.rank}.</span> <span className="text-text">{r.name}</span></span>
                    <span className="text-xs text-text-muted flex-shrink-0">{r.exact} exact · <strong className="text-text text-sm">{r.points}</strong> pts</span>
                  </li>
                ))}
              </ol>
              {data.player && (
                <div className="mt-3">
                  <ShareButton label="Challenge friends" text={`I'm playing the Bet Hope score challenge as ${data.player}. Can you beat me and the AI model this week?`}
                    url={typeof window !== 'undefined' ? `${window.location.origin}/game` : undefined} />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function JoinCard({ onJoined }: { onJoined: (token: string) => void }) {
  const [nick, setNick] = useState('');
  const [err, setErr] = useState('');
  const join = async () => {
    setErr('');
    try {
      const { data } = await api.post('/engage/game_join/', { nickname: nick.trim() });
      try { localStorage.setItem(TOKEN_KEY, data.token); } catch { /* private mode: works this session only */ }
      onJoined(data.token);
    } catch (e: any) {
      setErr(e?.response?.data?.error || 'Could not join');
    }
  };
  return (
    <div className="card card-compact mb-4">
      <div className="text-sm font-semibold text-text mb-1">Join with a nickname</div>
      <p className="text-xs text-text-muted mb-2">No account or email. Your nickname is kept on this device, so use the same phone each week.</p>
      <div className="flex gap-2 flex-wrap">
        <input value={nick} onChange={(e) => setNick(e.target.value)} placeholder="e.g. NaijaGaffer" maxLength={20} className="input input-sm flex-1 min-w-[160px]" aria-label="Nickname" />
        <button onClick={join} disabled={nick.trim().length < 3} className="btn btn-primary btn-sm">Join</button>
      </div>
      {err && <p className="text-xs text-red-400 mt-1">{err}</p>}
    </div>
  );
}

function MatchRow({ m, token, onSaved }: { m: any; token: string; onSaved: () => void }) {
  const [h, setH] = useState<string>(m.pick ? String(m.pick[0]) : '');
  const [a, setA] = useState<string>(m.pick ? String(m.pick[1]) : '');
  const [msg, setMsg] = useState('');
  const save = async () => {
    setMsg('');
    try {
      await api.post('/engage/game_pick/', { match_id: m.id, home: Number(h), away: Number(a) }, { headers: { 'X-Game-Token': token } });
      setMsg('Saved');
      onSaved();
    } catch (e: any) {
      setMsg(e?.response?.data?.error || 'Could not save');
    }
  };
  const ko = new Date(m.kickoff_at).toLocaleString(undefined, { weekday: 'short', hour: '2-digit', minute: '2-digit' });
  return (
    <li className="py-3">
      <div className="text-[11px] text-text-muted mb-1">{m.league} · {ko}</div>
      <div className="flex items-center gap-2">
        <span className="flex-1 min-w-0 text-sm text-text truncate text-right">{m.home}</span>
        {m.open && token ? (
          <>
            <input aria-label={`${m.home} goals`} inputMode="numeric" value={h} onChange={(e) => setH(e.target.value.replace(/\D/g, '').slice(0, 2))} className="input input-sm w-11 text-center" />
            <span className="text-text-muted">-</span>
            <input aria-label={`${m.away} goals`} inputMode="numeric" value={a} onChange={(e) => setA(e.target.value.replace(/\D/g, '').slice(0, 2))} className="input input-sm w-11 text-center" />
          </>
        ) : (
          <span className="text-sm font-bold text-text w-[104px] text-center">
            {m.score ? `${m.score[0]} - ${m.score[1]}` : m.pick ? `${m.pick[0]} - ${m.pick[1]}` : 'vs'}
          </span>
        )}
        <span className="flex-1 min-w-0 text-sm text-text truncate">{m.away}</span>
      </div>
      <div className="flex items-center justify-center gap-2 mt-1 text-[11px] text-text-muted">
        {m.open && token && <button onClick={save} disabled={h === '' || a === ''} className="btn btn-secondary btn-sm !py-0.5">{m.pick ? 'Update' : 'Save'}</button>}
        {m.score && m.pick && <span>Your pick {m.pick[0]}-{m.pick[1]} · <strong className="text-text">{m.points} pts</strong></span>}
        {!m.open && !m.score && <span>{m.pick ? `Your pick ${m.pick[0]}-${m.pick[1]} · ` : ''}in play / closed</span>}
        {msg && <span>{msg}</span>}
      </div>
    </li>
  );
}
