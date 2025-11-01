import os
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
import logging
logger = logging.getLogger(__name__)


def check_valid_input_date(input: str):
    datetime.strptime(input, "%d/%b")  # Check if the format is valid


def get_local_tz():
    # If the container sets TZ, use it. Otherwise, fall back to /etc/localtime
    tz_name = os.environ.get("TZ")
    if tz_name:
        return ZoneInfo(tz_name)

    # Try to read the system zone info symlink
    try:
        localtime_path = os.path.realpath("/etc/localtime")
        if "zoneinfo" in localtime_path:
            # Extract zone name from path, e.g. "/usr/share/zoneinfo/Europe/London"
            zone_name = localtime_path.split("zoneinfo/")[-1]
            return ZoneInfo(zone_name)
    except Exception:
        pass

    # Fallback if nothing else works
    return ZoneInfo("UTC")


def convert_input_to_date(input: str):
    logger.debug(f"Converting input date {input} to datetime")
    tz = get_local_tz()
    logger.debug(f"Current TZ is {tz}")
    now = datetime.now(tz)
    logger.debug(f"Now is {now}")

    parsed_date = datetime.strptime(input, "%d/%b")
    event_start = parsed_date.replace(year=now.year, hour=20, minute=0, second=0, microsecond=0, tzinfo=tz)
    # Handle if the parsed date is in the past by moving to the next year
    if event_start < now:
        event_start = event_start.replace(year=now.year + 1)

    logger.debug(f"start is {event_start}")

    return event_start


def get_next_day_occurrence(day_of_week: int = 2, at_time=time(hour=20, minute=0, second=0)):
    logger.debug(f"Getting next day occurence of {day_of_week} at {at_time}")
    tz = get_local_tz()
    now = datetime.now(tz)

    logger.debug(f"Tz is {tz}")
    logger.debug(f"now is {now}")

    # Ensure at least 7 days if today is requested day
    days_until_next_requested_day = (day_of_week - now.weekday() + 7) % 7 or 7
    event_start = now + timedelta(days=days_until_next_requested_day)
    event_start = event_start.replace(hour=at_time.hour, minute=at_time.minute, second=at_time.second)

    logger.debug(f"start is {event_start}")

    return event_start


def get_next_wednesdays(amount_to_generate: int = 4):
    today = datetime.now().astimezone()
    next_wednesdays = []

    # Find the next Wednesday
    days_until_next_wednesday = (2 - today.weekday() + 7) % 7 or 7
    next_wednesday = today + timedelta(days=days_until_next_wednesday)

    # Generate the next 4 Wednesdays
    for i in range(4):
        next_wednesdays.append(next_wednesday + timedelta(weeks=i))

    # Format as dd/MMM
    suggestions = [date.strftime("%d/%b") for date in next_wednesdays]

    return suggestions