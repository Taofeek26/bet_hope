"""
Season codes computed from the date (Phase 2, DATA-03 / ML-09).

Codes follow football-data.co.uk: '2627' = the 2026-27 season. Seasons
start in August for every league we track; a league with a different
start month passes it in (League.season_start_month).
"""
from datetime import date
from typing import List, Optional


def season_code_for(d: date, start_month: int = 8) -> str:
    """Season a date belongs to: 2026-09-30 -> '2627', 2026-05-10 -> '2526'."""
    start_year = d.year if d.month >= start_month else d.year - 1
    return f'{start_year % 100:02d}{(start_year + 1) % 100:02d}'


def current_season_code(start_month: int = 8, today: Optional[date] = None) -> str:
    return season_code_for(today or date.today(), start_month)


def recent_season_codes(n: int, start_month: int = 8, today: Optional[date] = None,
                        oldest: str = '9394') -> List[str]:
    """The current season and the n-1 before it, newest first ('2627', '2526', ...)."""
    start_year = int(current_season_code(start_month, today)[:2])
    # Codes use two-digit years; 93-99 are 1990s, everything else 2000s.
    full = 1900 + start_year if start_year >= 90 else 2000 + start_year
    codes = []
    for y in range(full, full - n, -1):
        code = f'{y % 100:02d}{(y + 1) % 100:02d}'
        codes.append(code)
        if code == oldest:
            break
    return codes


def all_season_codes(start_month: int = 8, today: Optional[date] = None) -> List[str]:
    """Every season football-data.co.uk has, newest first (back to 1993-94)."""
    return recent_season_codes(100, start_month, today, oldest='9394')


def season_name(code: str) -> str:
    """'2627' -> '2026-27', '9394' -> '1993-94'."""
    start = int(code[:2])
    century = 1900 if start >= 90 else 2000
    return f'{century + start}-{code[2:]}'
