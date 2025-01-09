import datetime

import discord
from discord import Interaction, Poll, PollMedia, PartialEmoji
from discord.ext import commands

from util import date_util


class PollAvailabilityCommand(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="availabilitypoll",
                                  description="Send a poll to guage availability for playing games.")
    async def availability_poll(self, interaction: Interaction, event_day: str):

        if event_day:
            try:
                date_util.check_valid_input_date(event_day)
            except ValueError:
                await interaction.response.send_message(
                    f"Invalid date format for `event_day`: `{event_day}`. Please use the format `dd/MMM` (e.g., `18/Dec`).",
                    ephemeral=True
                )
                return

        now = discord.utils.utcnow()
        event_date = date_util.convert_input_to_date(event_day)

        poll_end_date = event_date - datetime.timedelta(weeks=1)
        if poll_end_date < now:
            poll_end_date = event_date

        # Calculate poll duration
        duration = poll_end_date - now

        if duration > datetime.timedelta(days=31):
            duration = datetime.timedelta(days=31)

        poll = Poll(
            question=PollMedia(text=f"Are you available to play games on {event_day}?"),
            duration=duration
        )

        poll.add_answer(text="Yes", emoji="✅")
        poll.add_answer(text="No, maybe another day?", emoji="❓")
        poll.add_answer(text="No", emoji="❌")

        await interaction.response.send_message(
            poll=poll
        )


    @availability_poll.autocomplete("event_day")
    async def autocomplete_event_day(self, interaction: Interaction, current: str):
        """
        Autocomplete for the event_day parameter to suggest the next 4 Wednesdays.
        """
        suggestions = date_util.get_next_wednesdays(4)

        # Create Choices for autocomplete
        return [
            discord.app_commands.Choice(name=f"{suggestion}", value=suggestion)
            for suggestion in suggestions
        ]


# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(PollAvailabilityCommand(bot))
