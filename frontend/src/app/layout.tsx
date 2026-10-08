import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import '@/styles/globals.css';
import { Providers } from './providers';
import { SidebarProvider } from '@/contexts/SidebarContext';
import { SettingsProvider } from '@/contexts/SettingsContext';
import { Sidebar } from '@/components/layout/Sidebar';
import { MainContent } from '@/components/layout/MainContent';
import { NotificationWatcher } from '@/components/notifications/NotificationWatcher';
import { BetSlip } from '@/components/betslip/BetSlip';
import { PwaSetup } from '@/components/pwa/PwaSetup';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter', display: 'swap' });
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-jetbrains-mono', display: 'swap' });

export const metadata: Metadata = {
  title: 'Bet Hope - AI Football Predictions',
  description: 'AI-powered football match predictions and analytics platform',
  keywords: ['football', 'predictions', 'betting', 'AI', 'analytics', 'soccer'],
  metadataBase: new URL('https://bet-hope-frontend.vercel.app'),
  appleWebApp: { capable: true, title: 'Bet Hope', statusBarStyle: 'black-translucent' },
  icons: { apple: '/apple-touch-icon.png' },
  openGraph: {
    title: 'Bet Hope - AI Football Predictions',
    description: 'Match predictions for 20 leagues, measured honestly against the bookmakers.',
    siteName: 'Bet Hope',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>
          <SettingsProvider>
            <SidebarProvider>
              <div className="app">
                <Sidebar />
                <MainContent>
                  {children}
                </MainContent>
              </div>
              <NotificationWatcher />
              <BetSlip />
              <PwaSetup />
            </SidebarProvider>
          </SettingsProvider>
        </Providers>
      </body>
    </html>
  );
}
