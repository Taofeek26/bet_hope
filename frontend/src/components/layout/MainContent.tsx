'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/contexts/SidebarContext';
import { Header } from '@/components/layout/Header';

interface MainContentProps {
  children: ReactNode;
}

export function MainContent({ children }: MainContentProps) {
  const { collapsed } = useSidebar();

  return (
    <main className={cn('main-content', collapsed && 'main-content-expanded')}>
      <Header />
      {children}
    </main>
  );
}
