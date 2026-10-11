import { ImageResponse } from 'next/og';

// WhatsApp / Telegram link preview for a match (Phase 6): teams and the
// model's chances, so a shared link reads well in a group chat.
export const alt = 'Bet Hope match prediction';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';
export const revalidate = 3600;

const API = (process.env.NEXT_PUBLIC_API_URL || 'https://f7ce941v52.execute-api.us-east-1.amazonaws.com/prod/api') + '/v1';

export default async function Image({ params }: { params: { id: string } }) {
  let m: any = null;
  try {
    const r = await fetch(`${API}/matches/${params.id}/`, { next: { revalidate: 3600 } });
    if (r.ok) m = await r.json();
  } catch { /* fall back to a plain card */ }
  const home = m?.home_team?.name || 'Home';
  const away = m?.away_team?.name || 'Away';
  const p = m?.prediction?.probabilities;
  const pct = (x?: number) => (x == null ? '--' : `${Math.round(x * 100)}%`);
  const bar = (label: string, v?: number, hi?: boolean) => (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 300, padding: '24px 0', borderRadius: 20, background: hi ? '#0EA5E9' : '#1A1A1A' }}>
      <div style={{ fontSize: 30, color: hi ? '#03111A' : '#A3A3A3' }}>{label}</div>
      <div style={{ fontSize: 76, fontWeight: 700, color: hi ? '#03111A' : '#F5F5F5' }}>{pct(v)}</div>
    </div>
  );
  const top = p ? Math.max(p.home, p.draw, p.away) : -1;
  return new ImageResponse(
    (
      <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', padding: 60, background: '#0A0A0A', color: '#F5F5F5', fontFamily: 'sans-serif' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 34, color: '#7DD3FC' }}>
          <div style={{ width: 48, height: 48, borderRadius: 12, background: '#0EA5E9' }} />
          Bet Hope · {m?.league_name || 'Football prediction'}
        </div>
        <div style={{ display: 'flex', fontSize: 70, fontWeight: 700, marginTop: 50 }}>{home} v {away}</div>
        <div style={{ display: 'flex', gap: 30, marginTop: 50 }}>
          {bar(home.length > 14 ? 'Home' : home, p?.home, p?.home === top)}
          {bar('Draw', p?.draw, p?.draw === top)}
          {bar(away.length > 14 ? 'Away' : away, p?.away, p?.away === top)}
        </div>
        <div style={{ display: 'flex', marginTop: 'auto', fontSize: 26, color: '#A3A3A3' }}>Model chances, tested on 8,000+ past matches · 18+ bet responsibly</div>
      </div>
    ),
    size,
  );
}
