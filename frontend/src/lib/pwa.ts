import { create } from 'zustand';
import { engageApi } from '@/lib/api';

// Install-as-app and push alerts (Phase 6).
interface PwaState {
  installEvent: any | null;      // Chrome/Android "beforeinstallprompt"
  installed: boolean;
  setInstallEvent: (e: any | null) => void;
  setInstalled: (v: boolean) => void;
}
export const usePwa = create<PwaState>((set) => ({
  installEvent: null,
  installed: false,
  setInstallEvent: (installEvent) => set({ installEvent }),
  setInstalled: (installed) => set({ installed }),
}));

export const isIos = () => typeof navigator !== 'undefined' && /iphone|ipad|ipod/i.test(navigator.userAgent);
export const isStandalone = () =>
  typeof window !== 'undefined' && (window.matchMedia('(display-mode: standalone)').matches || (navigator as any).standalone === true);
export const pushSupported = () =>
  typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;

function b64ToBytes(b64: string) {
  const pad = '='.repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

export async function currentSubscription() {
  if (!pushSupported()) return null;
  const reg = await navigator.serviceWorker.getRegistration();
  return reg ? reg.pushManager.getSubscription() : null;
}

export async function subscribePush(teams: number[], prefs: Record<string, boolean>) {
  if (!pushSupported()) throw new Error('Push alerts are not supported in this browser');
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') throw new Error('Notifications are blocked for this site');
  const reg = await navigator.serviceWorker.register('/sw.js');
  await navigator.serviceWorker.ready;
  const { public_key } = await engageApi.pushKey();
  if (!public_key) throw new Error('Push alerts are not set up on the server yet');
  const sub = (await reg.pushManager.getSubscription()) || (await reg.pushManager.subscribe({
    userVisibleOnly: true, applicationServerKey: b64ToBytes(public_key),
  }));
  await engageApi.pushSubscribe(sub.toJSON(), teams, prefs);
  return sub;
}

export async function updatePush(teams: number[], prefs: Record<string, boolean>) {
  const sub = await currentSubscription();
  if (sub) await engageApi.pushSubscribe(sub.toJSON(), teams, prefs);
}

export async function unsubscribePush() {
  const sub = await currentSubscription();
  if (sub) {
    await engageApi.pushUnsubscribe(sub.endpoint);
    await sub.unsubscribe();
  }
}
