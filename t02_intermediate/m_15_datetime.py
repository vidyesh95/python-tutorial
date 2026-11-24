# Dates and Times
"""
datetime objects come in two flavours:
    naive  -> no timezone info (ambiguous; avoid in backend code)
    aware  -> carries a tzinfo (unambiguous)
Rules that prevent most bugs:
1. Store and compare times in UTC; convert to a local zone only for display.
2. Use aware datetimes: datetime.now(UTC), not datetime.now() or utcnow().
3. Use zoneinfo.ZoneInfo("Europe/Berlin") for real timezones (handles daylight saving).
4. Exchange timestamps as ISO 8601 strings: "2024-03-10T12:30:00+00:00".
timedelta represents a duration and supports arithmetic.
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

# Example: aware "now" in UTC and a fixed moment for reproducible output
now = datetime.now(UTC)
print("now is aware:", now.tzinfo is not None)

moment = datetime(2024, 3, 10, 12, 30, tzinfo=UTC)
print(moment, moment.year, moment.weekday())  # Monday == 0

# Example: converting between time zones (same instant, different wall clock)
tokyo = moment.astimezone(ZoneInfo("Asia/Tokyo"))
new_york = moment.astimezone(ZoneInfo("America/New_York"))
print(tokyo.isoformat(), new_york.isoformat())
print("same instant:", tokyo == new_york == moment)

# Example: daylight saving time is handled for you
before = datetime(2024, 3, 9, 12, 0, tzinfo=ZoneInfo("America/New_York"))
after = before + timedelta(days=1)  # wall-clock arithmetic across the DST change
print(before.utcoffset(), after.utcoffset())

# Example: timedelta arithmetic
delta = timedelta(days=1, hours=2, minutes=30)
print(delta, delta.total_seconds())
print(moment + delta, moment - timedelta(weeks=1))
print((datetime(2024, 12, 25, tzinfo=UTC) - moment).days, "days until Christmas")
print(date(2024, 3, 10) + timedelta(days=30))

# Example: ISO 8601 formatting and parsing
iso = moment.isoformat()
print(iso, datetime.fromisoformat(iso) == moment)
print(datetime.fromisoformat("2024-03-10T12:30:00Z"))  # 'Z' is accepted on 3.11+
print(datetime.fromisoformat("2024-03-10T18:00:00+05:30").astimezone(UTC))

# Example: strftime / strptime for custom formats
print(moment.strftime("%Y-%m-%d %H:%M"), moment.strftime("%A %d %B %Y"))
parsed = datetime.strptime("10/03/2024 08:15", "%d/%m/%Y %H:%M").replace(tzinfo=UTC)
print(parsed)

# Example: unix timestamps
ts = moment.timestamp()
print(ts, datetime.fromtimestamp(ts, tz=UTC) == moment)

# Example: naive and aware datetimes cannot be mixed
naive = datetime(2024, 3, 10, 12, 30)
try:
    _ = naive < moment
except TypeError as exc:
    print("TypeError:", exc)

# Example: start of day and truncation
print(moment.replace(hour=0, minute=0, second=0, microsecond=0))
print(moment.date(), moment.time())

# Example: comparing and sorting
stamps = [moment + timedelta(hours=h) for h in (5, 1, 3)]
print([s.hour for s in sorted(stamps)])

"""
Common mistakes
- datetime.now() / utcnow() give NAIVE values (utcnow is deprecated). Use datetime.now(UTC).
- Doing arithmetic in local time and being surprised by DST; compute in UTC.
- Comparing naive and aware datetimes (TypeError).
- Attaching a zone with .replace(tzinfo=...) to a time that was already in another zone;
  use .astimezone(...) to convert.
- Storing local time strings without an offset in a database.
- Mixing up month/day order when parsing; be explicit with strptime formats.
"""

"""
Where this shows up in backend/ML work
- created_at/updated_at columns, token expiry (JWT exp), cache TTLs and scheduling.
- Pydantic and FastAPI parse and emit ISO 8601 datetimes automatically.
- Time-series features, windowed aggregations and log analysis need correct time zones.
- Cloud APIs (S3, CloudWatch) return UTC timestamps you must handle correctly.
"""
