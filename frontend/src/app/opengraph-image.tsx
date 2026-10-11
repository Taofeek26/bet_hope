import { ImageResponse } from 'next/og';

// Link-preview image (Phase 4, UI-04), generated at build time from the
// same mark as icon.svg.
export const alt = 'Bet Hope - AI Football Predictions';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '80px',
          background: '#0A0A0A',
          color: '#F5F5F5',
          fontFamily: 'sans-serif',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '28px' }}>
          <svg width="120" height="120" viewBox="0 0 32 32">
            <rect width="32" height="32" rx="8" fill="#0EA5E9" />
            <polyline points="5,24 12,18 17,21 27,9" fill="none" stroke="#03111A" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="24" cy="23" r="4.2" fill="#FFFFFF" stroke="#03111A" strokeWidth="1.6" />
          </svg>
          <div style={{ fontSize: 96, fontWeight: 700 }}>Bet Hope</div>
        </div>
        <div style={{ fontSize: 44, marginTop: 40, color: '#7DD3FC' }}>AI football predictions for 20 leagues</div>
        <div style={{ fontSize: 32, marginTop: 16, color: '#A3A3A3' }}>Calibrated probabilities, measured against the bookmakers</div>
      </div>
    ),
    size,
  );
}
