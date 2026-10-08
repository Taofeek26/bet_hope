'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  Trophy,
  Calendar,
  BarChart3,
  TrendingUp,
  Star,
  Settings,
  HelpCircle,
  Zap,
  Target,
  ChevronLeft,
  ChevronRight,
  Terminal,
  Wallet,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/contexts/SidebarContext';
import { useModelInfo, useValueBets } from '@/hooks/useApi';
import { LogoMark } from '@/components/ui/Logo';

const navItems = [
  { href: '/', icon: Home, label: 'Dashboard', num: '1' },
  { href: '/predictions', icon: TrendingUp, label: 'Predictions', num: '2' },
  { href: '/matches', icon: Calendar, label: 'Matches', num: '3' },
  { href: '/leagues', icon: Trophy, label: 'Leagues', num: '4' },
  { href: '/analytics', icon: BarChart3, label: 'Analytics', num: '5' },
  { href: '/value-bets', icon: Target, label: 'Value Bets', num: '6' },
  { href: '/favorites', icon: Star, label: 'Favorites', num: '7' },
  { href: '/my-bets', icon: Wallet, label: 'My bets', num: '8' },
];

const bottomItems = [
  { href: '/admin', icon: Terminal, label: 'Admin' },
  { href: '/settings', icon: Settings, label: 'Settings' },
  { href: '/help', icon: HelpCircle, label: 'Help' },
];

export function Sidebar() {
  const pathname = usePathname();
  const { collapsed, toggle } = useSidebar();
  const { data: modelInfo } = useModelInfo();

  const { data: valueBets } = useValueBets();
  // No made-up fallback: show the version only once the API has answered.
  const modelVersion = modelInfo?.version;
  const valueCount = valueBets?.total;
  // "/leagues/E0" keeps "Leagues" highlighted; "/" only matches itself.
  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <aside className={cn('sidebar', collapsed && 'sidebar-collapsed')}>
      {/* Header */}
      {!collapsed && (
        <div className="sidebar-header">
          <div className="sidebar-badge">
            <Zap className="w-3 h-3" />
            <span>AI Powered</span>
          </div>
          <div className="flex items-center gap-2">
            <LogoMark className="w-7 h-7" />
            <h1 className="sidebar-title">Bet Hope</h1>
          </div>
          <p className="sidebar-desc">
            AI Football Predictions & Analytics Platform
          </p>
        </div>
      )}

      {/* Collapse Toggle */}
      <button
        onClick={toggle}
        className="sidebar-toggle"
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <ChevronLeft className="w-4 h-4" />
        )}
      </button>

      {/* Navigation */}
      <nav className="tabs-nav">
        {navItems.map((item) => (
          <NavItem
            key={item.href}
            {...item}
            badge={item.href === '/value-bets' && valueCount ? String(valueCount) : undefined}
            isActive={isActive(item.href)}
            collapsed={collapsed}
          />
        ))}

        {/* Divider */}
        <div className="my-3 mx-2 border-t border-border-dim" />

        {bottomItems.map((item) => (
          <NavItem
            key={item.href}
            {...item}
            isActive={isActive(item.href)}
            collapsed={collapsed}
          />
        ))}
      </nav>

      {/* Footer */}
      {!collapsed && (
        <div className="sidebar-footer">
          <div className="flex items-center gap-2 text-text-muted">
            <div className={cn('w-2 h-2 rounded-full', modelVersion ? 'bg-brand-1 animate-pulse' : 'bg-text-muted')} />
            <span>{modelVersion ? `Model ${modelVersion.split("_")[0]} live` : 'Model status unavailable'}</span>
          </div>
        </div>
      )}
    </aside>
  );
}

interface NavItemProps {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  num?: string;
  badge?: string;
  isActive: boolean;
  collapsed?: boolean;
}

function NavItem({ href, icon: Icon, label, num, badge, isActive, collapsed }: NavItemProps) {
  return (
    <Link
      href={href}
      className={cn('tab-btn', isActive && 'active')}
      aria-current={isActive ? 'page' : undefined}
      aria-label={collapsed ? label : undefined}
      title={collapsed ? label : undefined}
    >
      {num && !collapsed ? (
        <span className="tab-num">{num}</span>
      ) : (
        <Icon className="w-4 h-4" />
      )}
      {!collapsed && (
        <>
          <span className="tab-label">{label}</span>
          {badge && (
            <span className="tab-badge bg-brand/20 text-brand" title={`${badge} value bets right now`}>
              {badge}
            </span>
          )}
        </>
      )}
    </Link>
  );
}
