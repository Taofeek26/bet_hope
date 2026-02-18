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
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/contexts/SidebarContext';

const navItems = [
  { href: '/', icon: Home, label: 'Dashboard', num: '1' },
  { href: '/predictions', icon: TrendingUp, label: 'Predictions', num: '2' },
  { href: '/matches', icon: Calendar, label: 'Matches', num: '3' },
  { href: '/leagues', icon: Trophy, label: 'Leagues', num: '4' },
  { href: '/analytics', icon: BarChart3, label: 'Analytics', num: '5' },
  { href: '/value-bets', icon: Target, label: 'Value Bets', num: '6', badge: 'HOT' },
  { href: '/favorites', icon: Star, label: 'Favorites', num: '7' },
];

const bottomItems = [
  { href: '/settings', icon: Settings, label: 'Settings' },
  { href: '/help', icon: HelpCircle, label: 'Help' },
];

export function Sidebar() {
  const pathname = usePathname();
  const { collapsed, toggle } = useSidebar();

  return (
    <aside className={cn('sidebar', collapsed && 'sidebar-collapsed')}>
      {/* Header */}
      {!collapsed && (
        <div className="sidebar-header">
          <div className="sidebar-badge">
            <Zap className="w-3 h-3" />
            <span>AI Powered</span>
          </div>
          <h1 className="sidebar-title">Bet Hope</h1>
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
            isActive={pathname === item.href}
            collapsed={collapsed}
          />
        ))}

        {/* Divider */}
        <div className="my-3 mx-2 border-t border-border-dim" />

        {bottomItems.map((item) => (
          <NavItem
            key={item.href}
            {...item}
            isActive={pathname === item.href}
            collapsed={collapsed}
          />
        ))}
      </nav>

      {/* Footer */}
      {!collapsed && (
        <div className="sidebar-footer">
          <div className="flex items-center gap-2 text-text-muted">
            <div className="w-2 h-2 rounded-full bg-brand-1 animate-pulse" />
            <span>Model v2.1 Active</span>
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
            <span className="tab-badge bg-sky-500/20 text-sky-400">
              {badge}
            </span>
          )}
        </>
      )}
    </Link>
  );
}
