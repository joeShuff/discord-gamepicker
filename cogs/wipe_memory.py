from datetime import datetime

import discord
from discord import Interaction, ui
from discord.ext import commands
from discord.ui import Button

from db.database import fetch_game_from_db, get_all_server_games, fetch_game_with_memory, mark_game_logs_as_ignored


# Confirmation View with Buttons
class ConfirmationView(ui.View):
    def __init__(self, original_interaction: Interaction, server_id: str, game_name: str, memory_epoch: int = None):
        super().__init__(timeout=10)
        self.original_interaction = original_interaction
        self.server_id = server_id
        self.game_name = game_name
        self.memory_epoch = memory_epoch

    @discord.ui.button(label="Yes, wipe memory", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: Button):
        memory_date = None

        if self.memory_epoch:
            memory_date = datetime.fromtimestamp(self.memory_epoch)

        result = mark_game_logs_as_ignored(self.server_id, self.game_name, memory_date)

        if result:
            await interaction.response.edit_message(
                content="Memory for the game has been wiped successfully.",
                embed=None,
                view=None
            )
        else:
            await interaction.response.edit_message(
                content="There was a problem wiping the memory. Please check logs and report errors or try again.",
                embed=None,
                view=None
            )

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(
            content="Memory removal canceled.",
            embed=None,
            view=None
        )

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            memory_date = datetime.fromtimestamp(self.memory_epoch).strftime("%d %b %Y %H:%M") if self.memory_epoch else "all plays"
            embed = discord.Embed(
                title="⏱️ Wipe Memory Request Expired",
                description=f"The request to wipe memory for **{self.game_name}** ({memory_date}) has expired. Run `/wipegamememory` again if still needed.",
                color=discord.Color.dark_grey()
            )
            await self.original_interaction.edit_original_response(embed=embed, view=self)
        except discord.NotFound:
            pass


class GameWipeMemoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="wipegamememory", description="Clear game log memory for a game")
    async def wipe_game_memory(self, interaction: Interaction, game_name: str, memory_date: int = None):
        """Wipe the memory of a specific game (mark entries as ignored)."""
        server_id = str(interaction.guild.id)

        game = fetch_game_from_db(server_id, game_name)
        if game is None:
            await interaction.response.send_message("Error: No such game found.", ephemeral=True)
            return

        parsed_date = None

        if memory_date:
            game = fetch_game_with_memory(server_id, game_name)
            memory_datetime = datetime.fromtimestamp(memory_date)
            parsed_date = memory_datetime.strftime("%d %b %Y %H:%M")
            available_dates = [dt.strftime("%d %b %Y %H:%M") for dt in game.play_history]

            if parsed_date not in available_dates:
                await interaction.response.send_message(
                    f"Error: No log found for '{game_name}' on {parsed_date}.", ephemeral=True
                )
                return

        view = ConfirmationView(interaction, server_id, game_name, memory_date)

        if parsed_date:
            confirmation_message = f"Are you sure you want to wipe memory for {game_name} on {parsed_date}?"
        else:
            confirmation_message = f"Are you sure you want to wipe all memory for {game_name}?"

        await interaction.response.send_message(
            embed=discord.Embed(
                title=confirmation_message,
                description="This will remove play history related to this game. Proceed with caution.",
                color=discord.Color.red()
            ),
            view=view,
            ephemeral=True
        )

    @wipe_game_memory.autocomplete("game_name")
    async def autocomplete_games(self, interaction: Interaction, current: str):
        """Provide autocomplete suggestions for game names."""
        server_id = str(interaction.guild.id)
        game_names = get_all_server_games(server_id, search=current)[:25]

        return [
            discord.app_commands.Choice(name=game.name, value=game.name)
            for game in game_names
        ]

    @wipe_game_memory.autocomplete("memory_date")
    async def memory_date_autocomplete(self, interaction: Interaction, current: str):
        """Autocomplete function for memory dates based on the game name."""
        server_id = str(interaction.guild.id)
        game_name = interaction.namespace.game_name
        game = fetch_game_with_memory(server_id, game_name)

        return [
            discord.app_commands.Choice(name=date.strftime("%d %b %Y %H:%M"), value=date.timestamp())
            for date in game.play_history if date.strftime("%d %b %Y %H:%M").startswith(current)
        ]


# Add the cog to the bot
async def setup(bot):
    await bot.add_cog(GameWipeMemoryCog(bot))