import discord
from discord import Interaction, Embed
from discord.ext import commands

from game_db_controller import get_all_games


class ListGamesCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="listgames", description="List all games in the server.")
    async def list_games(self, interaction: Interaction):
        server_id = str(interaction.guild.id)
        games = get_all_games(server_id)

        if not games:
            await interaction.response.send_message("No games found. Add some first!", ephemeral=True)
            return

        embed = Embed(title="Games List", color=discord.Color.blue())
        for game in games:
            name, last_played, times_played = game
            last_played = last_played or "Never"
            embed.add_field(
                name=name,
                value=f"Last Played: {last_played}\nTimes Played: {times_played}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)


# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(ListGamesCommand(bot))
