from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from _loader import load

ex = load("t02_intermediate", "ex_15_datetime")


def test_to_utc():
    naive = datetime(2024, 1, 1, 12, 0)
    assert ex.to_utc(naive, "Asia/Tokyo") == datetime(2024, 1, 1, 3, 0, tzinfo=UTC)
    assert ex.to_utc(naive).hour == 12  # default assumes UTC
    aware = datetime(2024, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=2)))
    result = ex.to_utc(aware, "Asia/Tokyo")  # assume_tz ignored for aware input
    assert result.hour == 10 and result.utcoffset() == timedelta(0)


def test_to_utc_respects_dst():
    summer = ex.to_utc(datetime(2024, 7, 1, 12, 0), "America/New_York")
    winter = ex.to_utc(datetime(2024, 1, 1, 12, 0), "America/New_York")
    assert summer.hour == 16 and winter.hour == 17


def test_parse_iso_utc():
    assert ex.parse_iso_utc("2024-03-10T18:00:00+05:30").isoformat() == "2024-03-10T12:30:00+00:00"
    assert ex.parse_iso_utc("2024-03-10T12:30:00Z") == datetime(2024, 3, 10, 12, 30, tzinfo=UTC)
    assert ex.parse_iso_utc("2024-03-10T12:30:00").tzinfo is not None
    assert ex.parse_iso_utc("2024-03-10").hour == 0
    with pytest.raises(ValueError):
        ex.parse_iso_utc("not a date")


def test_add_business_days():
    friday = date(2024, 3, 8)
    assert ex.add_business_days(friday, 0) == friday
    assert ex.add_business_days(friday, 1) == date(2024, 3, 11)
    assert ex.add_business_days(date(2024, 3, 6), 5) == date(2024, 3, 13)
    assert ex.add_business_days(date(2024, 3, 9), 1) == date(2024, 3, 11)  # from a Saturday
    with pytest.raises(ValueError):
        ex.add_business_days(friday, -1)


def test_format_in_zone():
    dt = datetime(2024, 1, 1, 12, tzinfo=UTC)
    assert ex.format_in_zone(dt, "Asia/Tokyo") == "2024-01-01 21:00 JST"
    assert ex.format_in_zone(dt, "UTC") == "2024-01-01 12:00 UTC"
    with pytest.raises(ValueError):
        ex.format_in_zone(datetime(2024, 1, 1), "UTC")


def test_is_expired():
    issued = datetime(2024, 1, 1, 12, tzinfo=UTC)
    ttl = timedelta(hours=1)
    assert not ex.is_expired(issued, ttl, now=issued + timedelta(minutes=59))
    assert ex.is_expired(issued, ttl, now=issued + ttl)  # boundary counts as expired
    assert ex.is_expired(issued, ttl)  # real "now" is far in the future
    assert not ex.is_expired(datetime.now(UTC), timedelta(days=1))
    with pytest.raises(ValueError):
        ex.is_expired(datetime(2024, 1, 1), ttl)
    with pytest.raises(ValueError):
        ex.is_expired(issued, ttl, now=datetime(2024, 1, 2))
