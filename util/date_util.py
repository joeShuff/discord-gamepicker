from datetime import datetime, timedelta, time

import discord


def check_valid_input_date(input: str):
    datetime.strptime(input, "%d/%b")  # Check if the format is valid


def convert_input_to_date(input: str):
    now = discord.utils.utcnow()

    parsed_date = datetime.strptime(input, "%d/%b")
    event_start = parsed_date.replace(year=now.year, hour=20, minute=0, second=0, microsecond=0, tzinfo=now.tzinfo)
    # Handle if the parsed date is in the past by moving to the next year
    if event_start < now:
        event_start = event_start.replace(year=now.year + 1)

    return event_start


def get_next_day_occurrence(day_of_week: int = 2, at_time=time(hour=20, minute=0, second=0)):
    now = discord.utils.utcnow()

    # Ensure at least 7 days if today is requested day
    days_until_next_requested_day = (day_of_week - now.weekday() + 7) % 7 or 7
    event_start = now + timedelta(days=days_until_next_requested_day)
    event_start = event_start.replace(hour=at_time.hour, minute=at_time.minute, second=at_time.second)

    return event_start


def get_next_wednesdays(amount_to_generate: int = 4):
    today = discord.utils.utcnow()
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
