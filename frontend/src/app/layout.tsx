import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import '@/styles/globals.css';
import { Providers } from './providers';
import { SidebarProvider } from '@/contexts/SidebarContext';
import { Sidebar } from '@/components/layout/Sidebar';
import { MainContent } from '@/components/layout/MainContent';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
});

export const metadata: Metadata = {
  title: 'Bet Hope - AI Football Predictions',
  description: 'AI-powered football match predictions and analytics platform',
  keywords: ['football', 'predictions', 'betting', 'AI', 'analytics', 'soccer'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}>
        <Providers>
          <SidebarProvider>
            <div className="app">
              <Sidebar />
              <MainContent>
                {children}
              </MainContent>
            </div>
          </SidebarProvider>
        </Providers>
      </body>
    </html>
  );
}
