import type { MetadataRoute } from 'next';

// Install as an app (Phase 6): "Add to home screen" on Android and iPhone.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Bet Hope – AI Football Predictions',
    short_name: 'Bet Hope',
    description: 'Honest football predictions for 20 leagues: every market, the acca of the day, team news and results.',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: '#0A0A0A',
    theme_color: '#0A0A0A',
    icons: [
      { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
      { src: '/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  };
}
