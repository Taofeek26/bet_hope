// Nigerian bookmakers for "Open bookmaker" in the bet slip (Phase 5, step 3).
// None of them offers a public way to pre-fill a bet slip, so the slip is
// copied as text and the bookmaker's football page is opened. URLs checked
// 7 Oct 2026. Users should use a bookmaker licensed for their state.
export interface Bookmaker {
  id: string;
  name: string;
  url: string;
}

export const BOOKMAKERS: Bookmaker[] = [
  { id: 'bet9ja', name: 'Bet9ja', url: 'https://sports.bet9ja.com/' },
  { id: 'sportybet', name: 'SportyBet', url: 'https://www.sportybet.com/ng/sport/football' },
  { id: 'betking', name: 'BetKing', url: 'https://www.betking.com/sports/s/event/p/soccer' },
  { id: '1xbet', name: '1xBet Nigeria', url: 'https://1xbet.ng/en' },
  { id: 'betway', name: 'Betway Nigeria', url: 'https://www.betway.com.ng/sport/soccer' },
  { id: 'betano', name: 'Betano Nigeria', url: 'https://www.betano.ng/' },
  { id: 'msport', name: 'MSport', url: 'https://www.msport.com/ng/web' },
  { id: 'bangbet', name: 'BangBet', url: 'https://www.bangbet.com/ng' },
  { id: 'nairabet', name: 'NairaBet', url: 'https://www.nairabet.com/' },
];

export const bookmakerById = (id?: string) => BOOKMAKERS.find((b) => b.id === id);
