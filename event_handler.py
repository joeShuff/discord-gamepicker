import datetime
from typing import Optional

from discord.utils import MISSING
from discord import EntityType, ScheduledEvent
from discord import PrivacyLevel

from db.models import GameWithPlayHistory
from util import date_util


async def schedule_game_event(interaction, game: GameWithPlayHistory, event_day=None) -> tuple[ScheduledEvent, datetime.datetime]:
    """
    Schedules a Discord event for the chosen game.

    returns the start time of the event
    """
    guild = interaction.guild

    now = datetime.datetime.now().astimezone()
    event_start = now

    # If event_day is provided, validate and parse it
    if event_day:
        try:
            event_start = date_util.convert_input_to_date(event_day)
        except ValueError:
            await interaction.response.send_message(
                f"Invalid date format for event_day: `{event_day}`. Please use the format `dd/MMM` (e.g., `18/Dec`).",
                ephemeral=True
            )
            return None
    else:
        # Default to the next Wednesday at 8 PM UTC
        event_start = date_util.get_next_day_occurrence()

    event_end = event_start + datetime.timedelta(hours=2)  # Ends 2 hours later

    try:
        # Get the first available voice channel in the guild
        voice_channel = next((channel for channel in guild.voice_channels), None)
        if not voice_channel:
            await interaction.response.send_message(
                "Could not schedule event: No voice channels found.", ephemeral=True
            )
            return None

        # Handle image fetch if banner_link is provided
        event_image = MISSING
        if game.banner_link:
            try:
                event_image = await fetch_image(game.banner_link)
                if event_image is None:
                    raise ValueError("Image fetching returned None.")
            except Exception as e:
                await interaction.response.send_message(
                    f"Error fetching image: {e}", ephemeral=True
                )
                return None

        # Create the scheduled event
        scheduled_event = await guild.create_scheduled_event(
            name=f"🎮 {game.name}",
            start_time=event_start,
            end_time=event_end,
            description=f"Join us to play {game.name}! This game supports {game.min_players}-{game.max_players} players. {'[Steam Page](' + game.steam_link + ')' if game.steam_link else ''}",
            entity_type=EntityType.voice,  # Voice channel event
            channel=voice_channel,  # Associate event with the first available voice channel
            image=event_image,  # Use the fetched image or None if no image
            privacy_level=PrivacyLevel.guild_only,
            reason="Created for chosen scheduled game"
        )

        return scheduled_event, event_start
    except Exception as e:
        await interaction.response.send_message(
            f"Failed to schedule the event: {e}", ephemeral=True
        )
        raise e


async def fetch_image(image_url):
    """Fetch an image from a URL to use as a banner for the event."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            if response.status == 200:
                return await response.read()
            else:
                raise ValueError(f"Failed to fetch image: HTTP {response.status}")
