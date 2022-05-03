import zoneinfo
from datetime import datetime

from apitoolbox import tz

LOCAL_TZ = datetime.utcnow().astimezone().tzinfo
UTC_TZ = zoneinfo.ZoneInfo("UTC")


def test_as_datetime_str_with_tz():
    """Test `as_datetime` convert datetime with a timezone to UTC."""
    eastern_tz = zoneinfo.ZoneInfo("America/New_York")
    expected_dt = datetime(2020, 3, 20, tzinfo=eastern_tz)

    result = tz.as_datetime(expected_dt.isoformat())

    # `as_datetime` will convert it to UTC
    expected_dt -= eastern_tz.utcoffset(expected_dt)
    expected_dt = expected_dt.replace(tzinfo=UTC_TZ)
    assert result == expected_dt


def test_as_datetime_str_no_tz():
    """Test `as_datetime` set local timezone to datetime without a timezone
    and convert it to UTC."""
    expected_dt = datetime(2020, 3, 20, 0, 0)

    result = tz.as_datetime(expected_dt.isoformat())

    # `as_datetime` will assume that this is a local time and will adjust it
    # to UTC timezone
    expected_dt -= LOCAL_TZ.utcoffset(expected_dt)
    expected_dt = expected_dt.replace(tzinfo=UTC_TZ)
    assert result == expected_dt


def test_as_datetime_datetime_no_tz():
    """Test `as_datetime` set local timezone to datetime without a timezone
    and convert it to UTC."""
    expected_dt = datetime(2020, 3, 20, 0, 0)

    result = tz.as_datetime(expected_dt)

    # `as_datetime` will assume that this is a local time and will adjust it
    # to UTC timezone
    expected_dt -= LOCAL_TZ.utcoffset(expected_dt)
    expected_dt = expected_dt.replace(tzinfo=UTC_TZ)
    assert result == expected_dt


def test_utcnow():
    result = tz.utcnow()
    assert isinstance(result, datetime)
    assert result.tzinfo == UTC_TZ


def test_utcdatetime():
    args = (2020, 3, 20, 22, 45, 0)
    kwargs = dict(microsecond=0)

    result = tz.utcdatetime(*args, **kwargs)
    assert isinstance(result, datetime)
    assert result == datetime(*args, **kwargs, tzinfo=UTC_TZ)


def test_as_utc():
    eastern_tz = zoneinfo.ZoneInfo("America/New_York")
    value = datetime(2020, 3, 20, tzinfo=eastern_tz)

    result = tz.as_utc(value)
    expected_dt = value - eastern_tz.utcoffset(value)
    expected_dt = expected_dt.replace(tzinfo=UTC_TZ)
    assert result == expected_dt
