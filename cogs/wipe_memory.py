from datetime import datetime

import discord
from discord import Interaction, ui
from discord.ext import commands
from discord.ui import Button

from db.database import fetch_game_from_db, get_all_server_games, fetch_game_with_memory
from game_db_controller import mark_game_logs_as_ignored, fetch_log_dates_for_game


# Confirmation View with Buttons
class ConfirmationView(ui.View):
    def __init__(self, server_id: str, game_name: str, memory_date: str = None):
        super().__init__()
        self.server_id = server_id
        self.game_name = game_name
        self.memory_date = memory_date

    @discord.ui.button(label="Yes, wipe memory", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: Button):
        # Call the function to mark the game as ignored
        mark_game_logs_as_ignored(self.server_id, self.game_name, self.memory_date)

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
            view=None
        )


class GameWipeMemoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Command to wipe memory for a game
    @discord.app_commands.command(name="wipegamememory", description="Clear game log memory for a game")
    async def wipe_game_memory(self, interaction: Interaction, game_name: str, memory_date: str = None):
        """Wipe the memory of a specific game (mark entries as ignored)."""
        # Fetch the game details to confirm it exists
        server_id = str(interaction.guild.id)

        game = fetch_game_from_db(server_id, game_name)
        if game is None:
            await interaction.response.send_message("Error: No such game found.", ephemeral=True)
            return

        # Fetch available log dates for the game if memory_date is provided
        if memory_date:
            game = fetch_game_with_memory(server_id, game_name)
            available_dates = [dt.strftime("%d %b %Y %H:%M") for dt in game.play_history]

            if memory_date not in available_dates:
                await interaction.response.send_message(
                    f"Error: No log found for '{game_name}' on {memory_date}.", ephemeral=True
                )
                return

        # Create the confirmation view and pass the memory_date if provided
        view = ConfirmationView(server_id, game_name, memory_date)

        # Send confirmation message with buttons
        if memory_date:
            confirmation_message = f"Are you sure you want to wipe memory for {game_name} on {memory_date}?"
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
        game_names = get_all_server_games(server_id)  # Fetch a list of game names from the database

        return [
            discord.app_commands.Choice(name=game.name, value=game.name)
            for game in game_names if current.lower() in game.name.lower()
        ]

    @wipe_game_memory.autocomplete("memory_date")
    async def memory_date_autocomplete(self, interaction: Interaction, current: str):
        """Autocomplete function for memory dates based on the game name."""
        try:
            server_id = str(interaction.guild.id)

            # Retrieve the game_name option from the current interaction
            game_name = interaction.namespace.game_name

            # Fetch available log dates for the specified game
            game = fetch_game_with_memory(server_id, game_name)
            available_dates = [dt.strftime("%d %b %Y %H:%M") for dt in game.play_history]

            print(available_dates)

            # Filter dates that start with the current string typed by the user
            return [
                discord.app_commands.Choice(name=date,
                                            value=date)
                for date in available_dates if date.startswith(current)
            ]
        except Exception as e:
            print(e)


# Add the cog to the bot
async def setup(bot):
    await bot.add_cog(GameWipeMemoryCog(bot))
