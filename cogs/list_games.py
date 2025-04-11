import discord
from discord import Interaction, Embed
from discord.ext import commands

from game_db_controller import get_all_games_display, get_games_by_player_count


class ListGamesCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="listgames", description="List all games in the server.")
    async def list_games(self, interaction: Interaction, player_count: int = None):
        server_id = str(interaction.guild.id)

        if player_count:
            # Fetch games filtered by player_count
            games = get_games_by_player_count(server_id, player_count)
        else:
            # Fetch all games if player_count is not provided
            games = get_all_games_display(server_id)

        if not games:
            await interaction.response.send_message(
                f"No games found for {player_count} players. Add some first!" if player_count else "No games found. Add some first!",
                ephemeral=True
            )
            return

        # Modify the title based on the player_count
        embed_title = f"Games List for {player_count} Players" if player_count else "Games List"

        embed = Embed(title=embed_title, color=discord.Color.blue())
        for game in games:
            name, last_played, times_played, min_players, max_players = game
            last_played = last_played or "Never"
            embed.add_field(
                name=name,
                value=f"Last Played: {last_played}\nTimes Played: {times_played}\nPlayer Count: {min_players} - {max_players}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)


# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(ListGamesCommand(bot))

