"""Exercise 15: Dates and times.

Tasks
1. to_utc: convert a datetime (naive ones are assumed to be in a given zone) to UTC.
2. parse_iso_utc: parse ISO 8601 text into an aware UTC datetime.
3. add_business_days: skip weekends.
4. format_in_zone: display a datetime in another zone.
5. is_expired: TTL check that refuses naive datetimes.

Run: uv run pytest t02_intermediate -k datetime
"""

from datetime import date, datetime, timedelta


def to_utc(dt: datetime, assume_tz: str = "UTC") -> datetime:
    """Return dt converted to UTC (aware). A naive dt is interpreted in `assume_tz`.

    >>> to_utc(datetime(2024, 1, 1, 12, 0), "Asia/Tokyo").hour
    3
    """
    raise NotImplementedError


def parse_iso_utc(text: str) -> datetime:
    """Parse an ISO 8601 string (a trailing 'Z' means UTC). Naive input is assumed UTC.

    The result is always aware and in UTC. Raise ValueError for invalid text.

    >>> parse_iso_utc("2024-03-10T18:00:00+05:30").isoformat()
    '2024-03-10T12:30:00+00:00'
    """
    raise NotImplementedError


def add_business_days(start: date, days: int) -> date:
    """Move forward `days` weekdays (Mon-Fri), skipping Saturdays and Sundays.

    days == 0 returns start unchanged. Raise ValueError if days < 0.

    >>> add_business_days(date(2024, 3, 8), 1)  # a Friday
    datetime.date(2024, 3, 11)
    """
    raise NotImplementedError


def format_in_zone(dt: datetime, tz_name: str) -> str:
    """Format an AWARE datetime in tz_name as 'YYYY-MM-DD HH:MM ZONEABBR'.

    Raise ValueError for a naive datetime.

    >>> format_in_zone(datetime(2024, 1, 1, 12, tzinfo=UTC), "Asia/Tokyo")
    '2024-01-01 21:00 JST'
    """
    raise NotImplementedError


def is_expired(issued_at: datetime, ttl: timedelta, now: datetime | None = None) -> bool:
    """True when now >= issued_at + ttl. `now` defaults to the current UTC time.

    Raise ValueError if issued_at (or a given now) is naive.
    """
    raise NotImplementedError
