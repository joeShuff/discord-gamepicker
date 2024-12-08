import discord
from discord import Interaction, ui
from discord.ext import commands
from discord.ui import Button

from game_db_controller import fetch_game_from_db, mark_game_logs_as_ignored, fetch_game_names


# Confirmation View with Buttons
class ConfirmationView(ui.View):
    def __init__(self, server_id: str, game_name: str):
        super().__init__()
        self.server_id = server_id
        self.game_name = game_name

    @discord.ui.button(label="Yes, wipe memory", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: Button):
        # Call the function to mark the game as ignored
        mark_game_logs_as_ignored(self.server_id, self.game_name)

        # Acknowledge the action
        await interaction.response.edit_message(
            content="Memory for the game has been wiped successfully.",
            embed=None,
            view=None
        )

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(
            content="Memory removal canceled.",
            embed=None,
            view=None,
            ephemeral=True
        )


class GameWipeMemoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Command to wipe memory for a game
    @discord.app_commands.command(name="wipegamememory", description="Clear game log memory for a game")
    async def wipe_game_memory(self, interaction: Interaction, game_name: str):
        """Wipe the memory of a specific game (mark entries as ignored)."""
        # Fetch the game details to confirm it exists
        server_id = str(interaction.guild.id)

        game = fetch_game_from_db(server_id, game_name)
        if not game:
            await interaction.response.send_message("Error: No such game found.", ephemeral=True)
            return

        view = ConfirmationView(server_id, game_name)

        # Send confirmation message with buttons
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"Are you sure you want to wipe memory for {game_name}?",
                description="This will mark all play history related to this game as ignored.",
                color=discord.Color.red()
            ),
            view=view,
            ephemeral=True
        )

    @wipe_game_memory.autocomplete("game_name")
    async def autocomplete_games(self, interaction: Interaction, current: str):
        """Provide autocomplete suggestions for game names."""
        server_id = str(interaction.guild.id)
        game_names = fetch_game_names(server_id)  # Fetch a list of game names from the database

        return [
            discord.app_commands.Choice(name=game, value=game)
            for game in game_names if current.lower() in game.lower()
        ]

# Add the cog to the bot
async def setup(bot):
    await bot.add_cog(GameWipeMemoryCog(bot))
