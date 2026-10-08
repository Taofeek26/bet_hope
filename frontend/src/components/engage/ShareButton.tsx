'use client';

import { useState } from 'react';
import { Share2, Check } from 'lucide-react';

/**
 * Share to WhatsApp (Phase 6). Phones use the system share sheet (WhatsApp,
 * Telegram, ...); elsewhere it opens WhatsApp with the text ready.
 * The link carries a preview card, so it looks good in group chats.
 */
export function ShareButton({ text, url, label = 'Share', className = '' }: { text: string; url?: string; label?: string; className?: string }) {
  const [done, setDone] = useState(false);
  const link = url || (typeof window !== 'undefined' ? window.location.href : '');
  const message = `${text}\n${link}\n18+ · Bet responsibly`;
  const share = async () => {
    try {
      if (navigator.share) {
        await navigator.share({ text: message });
      } else {
        window.open(`https://wa.me/?text=${encodeURIComponent(message)}`, '_blank', 'noopener');
      }
      setDone(true);
      setTimeout(() => setDone(false), 2000);
    } catch {
      /* user cancelled the share sheet */
    }
  };
  return (
    <button onClick={share} className={`btn btn-secondary btn-sm ${className}`} aria-label={`${label} on WhatsApp or another app`}>
      {done ? <Check className="w-4 h-4" /> : <Share2 className="w-4 h-4" />}
      <span>{label}</span>
    </button>
  );
}
