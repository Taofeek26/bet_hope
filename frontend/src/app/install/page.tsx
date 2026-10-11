'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Download, Share, PlusSquare, Check, Copy, Smartphone } from 'lucide-react';
import { usePwa, isStandalone } from '@/lib/pwa';

type Env = 'installed' | 'ios-inapp' | 'ios-safari' | 'ios-other' | 'android' | 'desktop';

function detect(): Env {
  if (isStandalone()) return 'installed';
  const ua = navigator.userAgent;
  const ios = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  // Apps that open links in their own browser, where "Add to Home Screen" is missing.
  const inApp = /FBAN|FBAV|Instagram|Line\/|Twitter|Snapchat|TikTok|musical_ly|Bytedance|WhatsApp|Telegram|GSA\//i.test(ua);
  if (ios && inApp) return 'ios-inapp';
  if (ios && /CriOS|FxiOS|EdgiOS|OPiOS/i.test(ua)) return 'ios-other';
  if (ios) return 'ios-safari';
  if (/android/i.test(ua)) return 'android';
  return 'desktop';
}

/** How to install Bet Hope as an app, for the browser you're in (Phase 7). */
export default function InstallPage() {
  const { installEvent, setInstallEvent } = usePwa();
  const [env, setEnv] = useState<Env | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => setEnv(detect()), []);
  const link = typeof window !== 'undefined' ? window.location.origin : 'https://bet-hope-frontend.vercel.app';
  const copy = async () => { try { await navigator.clipboard.writeText(link); } catch { window.prompt('Copy this link:', link); } setCopied(true); };
  const install = async () => { installEvent.prompt(); await installEvent.userChoice.catch(() => null); setInstallEvent(null); };

  return (
    <>
      <div className="content-header">
        <h1>Install Bet Hope</h1>
        <p>Put Bet Hope on your home screen: it opens like an app, full screen, and can send you alerts.</p>
      </div>
      <div className="card max-w-xl">
        {!env ? null : env === 'installed' ? (
          <Done />
        ) : env === 'ios-inapp' ? (
          <>
            <h2 className="card-title mb-2">First, open this page in Safari</h2>
            <p className="text-sm text-text-sec mb-3">You opened Bet Hope inside another app (WhatsApp, Instagram, Facebook…). iPhones only allow installing from <strong>Safari</strong>.</p>
            <ol className="space-y-2 text-sm text-text-sec list-decimal pl-5 mb-4">
              <li>Tap the <strong>⋯</strong> or <strong>Share</strong> button in this app and choose <strong>Open in Safari</strong>, or</li>
              <li>copy the link below, open <strong>Safari</strong>, paste it in the address bar, then follow the steps on this page again.</li>
            </ol>
            <button onClick={copy} className="btn btn-primary btn-sm">{copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />} {copied ? 'Link copied' : 'Copy link'}</button>
          </>
        ) : env === 'ios-safari' || env === 'ios-other' ? (
          <>
            {env === 'ios-other' && <p className="text-sm text-amber-400 mb-3">Tip: this works best in <strong>Safari</strong>. In Chrome, Edge or Firefox on iPhone (iOS 16.4 or later) use the Share button next to the address bar; on older iPhones open the page in Safari.</p>}
            <h2 className="card-title mb-3">Three taps in Safari</h2>
            <ol className="space-y-4 text-sm text-text-sec">
              <Step n={1} icon={<Share className="w-5 h-5 text-brand" />}>Tap the <strong>Share</strong> button (the square with an arrow pointing up) at the <strong>bottom</strong> of the screen{env === 'ios-other' ? ' or next to the address bar' : ''}.</Step>
              <Step n={2} icon={<PlusSquare className="w-5 h-5 text-brand" />}>Scroll down the list and tap <strong>Add to Home Screen</strong>. (If it&apos;s missing, tap <strong>Edit Actions</strong> at the bottom and add it.)</Step>
              <Step n={3} icon={<Check className="w-5 h-5 text-brand" />}>Tap <strong>Add</strong> (top right). Bet Hope appears on your home screen.</Step>
            </ol>
            <p className="text-xs text-text-muted mt-4">Then open Bet Hope <strong>from the home-screen icon</strong> and go to <Link href="/settings" className="text-brand">Settings → Notifications</Link> to turn on alerts (needs iOS 16.4 or later).</p>
          </>
        ) : env === 'android' ? (
          <>
            <h2 className="card-title mb-3">Install on Android</h2>
            {installEvent ? (
              <button onClick={install} className="btn btn-primary mb-3"><Download className="w-4 h-4" /> Install Bet Hope</button>
            ) : null}
            <ol className="space-y-3 text-sm text-text-sec list-decimal pl-5">
              <li>{installEvent ? 'Or tap' : 'Tap'} the <strong>⋮</strong> menu at the top right of Chrome.</li>
              <li>Tap <strong>Install app</strong> (or <strong>Add to Home screen</strong>), then <strong>Install</strong>.</li>
            </ol>
            <p className="text-xs text-text-muted mt-4">Not Chrome? Samsung Internet: menu ☰ → Add page to → Home screen. Then turn on alerts in <Link href="/settings" className="text-brand">Settings → Notifications</Link>.</p>
          </>
        ) : (
          <>
            <h2 className="card-title mb-3">On a computer</h2>
            {installEvent && <button onClick={install} className="btn btn-primary mb-3"><Download className="w-4 h-4" /> Install Bet Hope</button>}
            <p className="text-sm text-text-sec">In Chrome or Edge, click the install icon at the right end of the address bar, or menu → <strong>Install Bet Hope</strong>.</p>
            <p className="text-sm text-text-sec mt-3 flex items-center gap-2"><Smartphone className="w-4 h-4 text-brand" /> On your phone, open <strong>{link.replace('https://', '')}</strong> and come back to this page.</p>
          </>
        )}
      </div>
    </>
  );
}

function Step({ n, icon, children }: { n: number; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className="w-7 h-7 rounded-full bg-brand/15 text-brand text-sm font-bold flex items-center justify-center flex-shrink-0">{n}</span>
      <span className="flex-1">{children}</span>
      <span className="flex-shrink-0">{icon}</span>
    </li>
  );
}

function Done() {
  return (
    <>
      <h2 className="card-title mb-2 flex items-center gap-2"><Check className="w-5 h-5 text-green-500" /> Bet Hope is installed</h2>
      <p className="text-sm text-text-sec">You&apos;re using the app from your home screen. Turn on alerts in <Link href="/settings" className="text-brand">Settings → Notifications</Link> for the morning acca, your teams and your results.</p>
    </>
  );
}
