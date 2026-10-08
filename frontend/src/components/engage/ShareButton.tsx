'use client';

import { useEffect, useRef, useState } from 'react';
import { Share2, Check, Copy, Send, MoreHorizontal } from 'lucide-react';

/**
 * Share menu (Phase 6). WhatsApp and Telegram are explicit choices: the
 * system share sheet doesn't list WhatsApp on computers (and some phone
 * browsers), which is why it used to be missing. "More apps" opens the
 * system sheet where the browser has one. Links carry a preview card.
 */
export function ShareButton({ text, url, label = 'Share', className = '', up = false }: { text: string; url?: string; label?: string; className?: string; up?: boolean }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [canNative, setCanNative] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => setCanNative(typeof navigator !== 'undefined' && !!navigator.share), []);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [open]);

  const link = url || (typeof window !== 'undefined' ? window.location.href : '');
  const message = `${text}\n${link}\n18+ · Bet responsibly`;
  const go = (href: string) => { window.open(href, '_blank', 'noopener'); setOpen(false); };
  const copy = async () => {
    try { await navigator.clipboard.writeText(message); } catch { window.prompt('Copy this:', message); }
    setCopied(true);
    setTimeout(() => { setCopied(false); setOpen(false); }, 1200);
  };
  const native = async () => {
    try { await navigator.share({ text: message }); } catch { /* cancelled */ }
    setOpen(false);
  };

  return (
    <div className="relative inline-block" ref={ref}>
      <button onClick={() => setOpen(!open)} className={`btn btn-secondary btn-sm ${className}`} aria-haspopup="menu" aria-expanded={open} aria-label={label || 'Share'}>
        <Share2 className="w-4 h-4" />
        {label && <span>{label}</span>}
      </button>
      {open && (
        <div role="menu" className={`absolute z-[60] right-0 w-48 ${up ? 'bottom-full mb-1' : 'mt-1'} bg-card border border-border rounded-lg shadow-xl p-1 text-sm`}>
          <button role="menuitem" onClick={() => go(`https://wa.me/?text=${encodeURIComponent(message)}`)} className="w-full flex items-center gap-2 px-3 py-2 rounded hover:bg-surface text-text">
            <span className="w-4 h-4 rounded-full bg-green-500 inline-flex items-center justify-center text-[9px] font-bold text-white">W</span> WhatsApp
          </button>
          <button role="menuitem" onClick={() => go(`https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(`${text}\n18+ · Bet responsibly`)}`)} className="w-full flex items-center gap-2 px-3 py-2 rounded hover:bg-surface text-text">
            <Send className="w-4 h-4 text-sky-400" /> Telegram
          </button>
          <button role="menuitem" onClick={copy} className="w-full flex items-center gap-2 px-3 py-2 rounded hover:bg-surface text-text">
            {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4 text-text-muted" />} {copied ? 'Copied' : 'Copy text'}
          </button>
          {canNative && (
            <button role="menuitem" onClick={native} className="w-full flex items-center gap-2 px-3 py-2 rounded hover:bg-surface text-text">
              <MoreHorizontal className="w-4 h-4 text-text-muted" /> More apps…
            </button>
          )}
        </div>
      )}
    </div>
  );
}
