import { create } from 'zustand';
import { accountApi, authApi, type Me } from '@/lib/api';

// Signed-in user (Phase 7). Tokens live in localStorage ('token', 'refresh'),
// the same keys the admin page already uses.
interface AuthState {
  user: Me | null;
  loading: boolean;
  setUser: (u: Me | null) => void;
  load: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  setUser: (user) => set({ user }),
  load: async () => {
    if (typeof window === 'undefined' || !localStorage.getItem('token')) return set({ user: null, loading: false });
    try { set({ user: await accountApi.me(), loading: false }); } catch { set({ user: null, loading: false }); }
  },
  login: async (email, password) => {
    const { access, refresh } = await authApi.login(email.trim().toLowerCase(), password);
    localStorage.setItem('token', access);
    localStorage.setItem('refresh', refresh);
    set({ user: await accountApi.me() });
  },
  register: async (email, password, name) => {
    const r = await accountApi.register(email.trim().toLowerCase(), password, name);
    localStorage.setItem('token', r.access);
    localStorage.setItem('refresh', r.refresh);
    set({ user: r.user });
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh');
    set({ user: null });
    // A shared phone must not keep the previous user's bets and favourites.
    window.dispatchEvent(new Event('bethope-signed-out'));
  },
}));
