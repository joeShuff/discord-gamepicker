import datetime
from discord.utils import utcnow, MISSING
from discord import EntityType
from discord import PrivacyLevel


async def schedule_game_event(interaction, game):
    """Schedules a Discord event for the chosen game."""
    guild = interaction.guild

    # Extract details from the game
    game_id, name, steam_link, banner_link, *_ = game

    # Calculate the event start and end times
    now = utcnow()  # Current UTC time
    event_start = now + datetime.timedelta(days=(2 - now.weekday()) % 7)  # Next Wednesday
    event_start = event_start.replace(hour=20, minute=0, second=0, microsecond=0)  # 8:00 PM UTC
    event_end = event_start + datetime.timedelta(hours=2)  # Ends 2 hours later

    try:
        # Get the first available voice channel in the guild
        voice_channel = next((channel for channel in guild.voice_channels), None)
        if not voice_channel:
            await interaction.response.send_message(
                "Could not schedule event: No voice channels found.", ephemeral=True
            )
            return

        # Handle image fetch if banner_link is provided
        event_image = MISSING
        if banner_link:
            try:
                event_image = await fetch_image(banner_link)
                if event_image is None:
                    raise ValueError("Image fetching returned None.")
            except Exception as e:
                await interaction.response.send_message(
                    f"Error fetching image: {e}", ephemeral=True
                )
                return

        # Create the scheduled event
        scheduled_event = await guild.create_scheduled_event(
            name=f"🎮 {name}",
            start_time=event_start,
            end_time=event_end,
            description=f"Join us to play {name}! {'[Steam Page](' + steam_link + ')' if steam_link else ''}",
            entity_type=EntityType.voice,  # Voice channel event
            channel=voice_channel,  # Associate event with the first available voice channel
            image=event_image,  # Use the fetched image or None if no image
            privacy_level=PrivacyLevel.guild_only,
            reason="Created for chosen scheduled game"
        )
        return scheduled_event
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
