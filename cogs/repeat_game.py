import logging

import discord
from discord import Interaction, Embed, ui
from discord.ext import commands

from db.database import get_most_recent_game_played, log_game_selection, fetch_game_with_memory, \
    get_all_server_games_including_archived
from event_handler import schedule_game_event

logger = logging.getLogger(__name__)


class RepeatGameConfirmation(ui.View):
    def __init__(self, game):
        super().__init__(timeout=300)
        self.game = game

    @ui.button(label="Repeat Game", style=discord.ButtonStyle.success, emoji="🔁")
    async def confirm(self, interaction: Interaction, button: ui.Button):
        # Disable the buttons immediately so the event can't be created twice.
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="Creating next week's event...",
            embed=None,
            view=self
        )

        try:
            scheduled_event, event_date = await schedule_game_event(
                interaction,
                self.game
            )

            if scheduled_event is None:
                return

            # Record this as a repeat. It remains in the history but won't
            # contribute to the normal play count.
            log_game_selection(
                self.game.id,
                event_date,
                repeat=True
            )

            embed = Embed(
                title="🔁 Game Repeated!",
                description=(
                    f"**{self.game.name}** will be played again next week! 🎮"
                ),
                color=discord.Color.green()
            )

            if self.game.banner_link:
                embed.set_image(url=self.game.banner_link)

            embed.add_field(
                name="Event",
                value=f"[View Event]({scheduled_event.url})",
                inline=False
            )

            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=None
            )

        except Exception as e:
            logger.exception("Failed to repeat game")

            embed = Embed(
                title="❌ Failed to Repeat Game",
                description=(
                    f"I couldn't create the event for **{self.game.name}**."
                ),
                color=discord.Color.red()
            )

            await interaction.edit_original_response(
                content=None,
                embed=embed,
                view=None
            )

        self.stop()

    @ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        self.stop()

        embed = Embed(
            title="Repeat Cancelled",
            description="No event was created.",
            color=discord.Color.dark_grey()
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None
        )

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title="⏱️ Repeat Game Timed Out",
            description="This confirmation has timed out. No event was created.",
            color=discord.Color.dark_grey()
        )

        try:
            await self.message.edit(
                content=None,
                embed=embed,
                view=self
            )
        except (discord.NotFound, discord.HTTPException):
            pass


class RepeatGameCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(
        name="repeatgame",
        description="Repeat a game next week."
    )
    @discord.app_commands.describe(
        game="The game to repeat. Leave blank to repeat the most recently played game."
    )
    async def repeat_game(
            self,
            interaction: Interaction,
            game: str | None = None
    ):
        server_id = str(interaction.guild.id)

        if game:
            # Find the requested game
            selected_game = fetch_game_with_memory(server_id, game)

            if selected_game is None:
                await interaction.response.send_message(
                    f"I couldn't find a game called **{game}**.",
                    ephemeral=True
                )
                return

            recent_game = selected_game
            last_played = selected_game.play_history[0] if selected_game.play_history else None

        else:
            result = get_most_recent_game_played(server_id)

            if result is None:
                await interaction.response.send_message(
                    "There isn't a recently played game to repeat!",
                    ephemeral=True
                )
                return

            recent_game, last_played = result

        embed = Embed(
            title="🔁 Repeat Game?",
            description=(
                f"You have recently played:\n"
                f"## 🎮 {recent_game.name}\n\n"
                f"Do you want to play **{recent_game.name}** again next week?"
            ),
            color=discord.Color.orange()
        )

        embed.add_field(
            name="Last Played",
            value=last_played.strftime("%d %B %Y"),
            inline=True
        )

        if recent_game.banner_link:
            embed.set_image(url=recent_game.banner_link)

        embed.add_field(
            name="Players",
            value=f"{recent_game.min_players} - {recent_game.max_players}",
            inline=True
        )

        if recent_game.steam_link:
            embed.add_field(
                name="Steam",
                value=f"[View on Steam]({recent_game.steam_link})",
                inline=True
            )

        view = RepeatGameConfirmation(recent_game)

        await interaction.response.send_message(
            embed=embed,
            view=view
        )

        view.message = await interaction.original_response()

    @repeat_game.autocomplete("game")
    async def autocomplete_games(self, interaction: Interaction, current: str):
        """Provide autocomplete suggestions for game names (includes archived games)."""
        server_id = str(interaction.guild.id)
        games = get_all_server_games_including_archived(server_id, search=current)[:25]
        return [
            discord.app_commands.Choice(name=game.name, value=game.name)
            for game in games
        ]

async def setup(bot):
    await bot.add_cog(RepeatGameCommand(bot))