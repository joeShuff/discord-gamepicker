import sqlite3

import discord
from discord import Interaction
from discord.ext import commands

from game_db_controller import add_game_to_db


class AddGameCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="addgame", description="Add a new game to the list.")
    async def add_game(
            self,
            interaction: Interaction,
            name: str,
            min_players: int,
            max_players: int,
            steam_link: str = None,
            banner_link: str = None):

        server_id = str(interaction.guild.id)
        try:
            add_game_to_db(server_id, name, min_players, max_players, steam_link, banner_link)
            await interaction.response.send_message(f"'{name}' has been added to t’list!")
        except sqlite3.IntegrityError:
            await interaction.response.send_message("Error: Game already exists.")


# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(AddGameCommand(bot))
