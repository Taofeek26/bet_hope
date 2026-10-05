"""
Kickoff time helpers (Phase 2, DATA-06).

Providers report kickoff in different zones: football-data.org in UTC,
football-data.co.uk in UK local time. Match.kickoff_at stores the one
unambiguous instant (UTC); the browser formats it in the user's zone.
"""
from datetime import date, datetime, time, timezone as dt_timezone
from typing import Optional
from zoneinfo import ZoneInfo


def local_to_utc(d: date, t: Optional[time], tz_name: str) -> Optional[datetime]:
    """Combine a local date + time in `tz_name` into an aware UTC datetime."""
    if d is None or t is None:
        return None
    local = datetime.combine(d, t).replace(tzinfo=ZoneInfo(tz_name))
    return local.astimezone(dt_timezone.utc)
