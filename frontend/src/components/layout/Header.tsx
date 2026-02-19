'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Menu, Search, Bell, User } from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';
import { TaskStatusIndicator } from '@/components/ui/TaskStatusIndicator';

export function Header() {
  const { toggleSidebar } = useAppStore();
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 bg-background-secondary/80 backdrop-blur-sm border-b border-slate-700/50">
      <div className="flex items-center justify-between h-16 px-4">
        {/* Left */}
        <div className="flex items-center gap-4">
          <button
            onClick={toggleSidebar}
            className="lg:hidden p-2 rounded-lg hover:bg-slate-700 text-slate-400"
          >
            <Menu className="w-5 h-5" />
          </button>

          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
              <span className="text-white font-bold text-sm">BH</span>
            </div>
            <span className="hidden sm:block text-lg font-semibold text-white">
              Bet Hope
            </span>
          </Link>
        </div>

        {/* Center - Search */}
        <div className="flex-1 max-w-xl mx-4 hidden md:block">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search teams, matches..."
              className="w-full pl-10 pr-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white placeholder-slate-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
        </div>

        {/* Right */}
        <div className="flex items-center gap-2">
          {/* Mobile search toggle */}
          <button
            onClick={() => setSearchOpen(!searchOpen)}
            className="md:hidden p-2 rounded-lg hover:bg-slate-700 text-slate-400"
          >
            <Search className="w-5 h-5" />
          </button>

          {/* Task Status Indicator */}
          <TaskStatusIndicator />

          {/* Notifications */}
          <button className="relative p-2 rounded-lg hover:bg-slate-700 text-slate-400">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
          </button>

          {/* User menu */}
          <button className="p-2 rounded-lg hover:bg-slate-700 text-slate-400">
            <User className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Mobile search dropdown */}
      {searchOpen && (
        <div className="md:hidden p-4 border-t border-slate-700/50">
          <input
            type="text"
            placeholder="Search teams, matches..."
            className="w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-white placeholder-slate-400 focus:border-primary-500 focus:outline-none"
            autoFocus
          />
        </div>
      )}
    </header>
  );
}
