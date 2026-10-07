import { useId } from 'react';

/**
 * Bet Hope mark (Phase 4, UI-04): a ball on a rising trend line, in the
 * brand sky blue. The same drawing is used for the browser icon
 * (src/app/icon.svg), so keep the two in step.
 */
export function LogoMark({ className = 'w-8 h-8' }: { className?: string }) {
  // A unique gradient id per copy: with one shared id, the copy in the
  // sidebar header (hidden on phones) owned the gradient and every other
  // copy rendered without its background, as a lone dot.
  const gid = `bh-grad-${useId().replace(/:/g, '')}`;
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#0EA5E9" />
          <stop offset="1" stopColor="#7DD3FC" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8" fill={`url(#${gid})`} />
      <polyline points="5,24 12,18 17,21 27,9" fill="none" stroke="#03111A" strokeWidth="2.6"
        strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="24" cy="23" r="4.2" fill="#FFFFFF" stroke="#03111A" strokeWidth="1.6" />
      <path d="M24 20.2 l1.6 1.2 -0.6 1.9 h-2 l-0.6-1.9z" fill="#03111A" />
    </svg>
  );
}

export function Logo({ showText = true }: { showText?: boolean }) {
  return (
    <span className="flex items-center gap-2">
      <LogoMark />
      {showText && <span className="text-lg font-semibold text-text">Bet Hope</span>}
    </span>
  );
}
