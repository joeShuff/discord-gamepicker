import sqlite3

import discord
from discord import Interaction
from discord.ext import commands

from db.database import add_game_to_db, get_least_playcount_for_server
from db.models import Game


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
            playcount_offset = get_least_playcount_for_server(server_id)

            game = Game(
                server_id=server_id,
                name=name,
                min_players=min_players,
                max_players=max_players,
                steam_link=steam_link,
                banner_link=banner_link,
                playcount_offset=playcount_offset
            )
            add_game_to_db(game)
            await interaction.response.send_message(f"'{name}' has been added to t’list!")
        except sqlite3.IntegrityError:
            await interaction.response.send_message("Error: Game already exists.")
        except Exception as e:
            print(e)


# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(AddGameCommand(bot))
