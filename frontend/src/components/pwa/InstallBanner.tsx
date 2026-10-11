'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Download, X } from 'lucide-react';
import { usePwa, isIos, isStandalone } from '@/lib/pwa';

/** "Install Bet Hope" on the Dashboard: a native prompt on Android/desktop, steps on iPhone. */
export function InstallBanner() {
  const { installEvent, installed, setInstallEvent } = usePwa();
  const [hidden, setHidden] = useState(true);
  const [ios, setIos] = useState(false);
  useEffect(() => {
    let dismissed = false;
    try { dismissed = localStorage.getItem('bethope_install_dismissed') === '1'; } catch { /* show */ }
    setIos(isIos() && !isStandalone());
    setHidden(dismissed || isStandalone());
  }, []);
  if (hidden || installed || (!installEvent && !ios)) return null;

  const dismiss = () => { try { localStorage.setItem('bethope_install_dismissed', '1'); } catch { /* ignore */ } setHidden(true); };
  const install = async () => {
    installEvent.prompt();
    await installEvent.userChoice.catch(() => null);
    setInstallEvent(null);
  };
  return (
    <div className="card card-compact mb-6 flex items-center gap-3">
      <Download className="w-5 h-5 text-brand flex-shrink-0" />
      <div className="flex-1 min-w-0 text-sm">
        <div className="text-text font-semibold">Install Bet Hope</div>
        <div className="text-xs text-text-muted">
          {ios ? <>On iPhone: Safari → <strong>Share</strong> → <strong>Add to Home Screen</strong>.</>
               : 'Opens like an app, with morning alerts for the acca, top picks and your teams.'}
        </div>
      </div>
      {ios
        ? <Link href="/install" className="btn btn-primary btn-sm flex-shrink-0">How to</Link>
        : <button onClick={install} className="btn btn-primary btn-sm flex-shrink-0">Install</button>}
      <button onClick={dismiss} className="text-text-muted hover:text-text flex-shrink-0" aria-label="Dismiss"><X className="w-4 h-4" /></button>
    </div>
  );
}
