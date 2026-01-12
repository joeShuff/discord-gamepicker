import discord
from discord import Interaction, Embed
from discord.ext import commands

from db.database import get_all_server_games, get_eligible_games


class ListGamesCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="listgames", description="List all games in the server.")
    async def list_games(self, interaction: Interaction, player_count: int = None):
        server_id = str(interaction.guild.id)

        if player_count:
            # Fetch games filtered by player_count
            games = get_eligible_games(server_id, player_count)
        else:
            # Fetch all games if player_count is not provided
            games = get_all_server_games(server_id)

        if not games:
            await interaction.response.send_message(
                f"No games found for {player_count} players. Add some first!" if player_count else "No games found. Add some first!",
                ephemeral=True
            )
            return

        # Modify the title based on the player_count
        embed_title = f"Games List for {player_count} Players" if player_count else "Games List"

        # Split games into chunks of 25 for multiple embeds
        chunk_size = 25
        total_pages = (len(games) - 1) // chunk_size + 1
        embeds = []

        for page in range(total_pages):
            start = page * chunk_size
            end = start + chunk_size
            chunk = games[start:end]
            page_num = page + 1
            current_title = f"{embed_title} (Page {page_num}/{total_pages})" if total_pages > 1 else embed_title
            embed = Embed(title=current_title, color=discord.Color.blue())
            
            for game in chunk:
                last_played = "Never"
                if game.play_history:
                    last_played = game.play_history[0].strftime("%d %b %Y")
                embed.add_field(
                    name=game.name,
                    value=f"Last Played: {last_played}\n"
                          f"Times Played: {len(game.play_history)}\n"
                          f"Player Count: {game.min_players} - {game.max_players}",
                    inline=False,
                )
            embeds.append(embed)

        await interaction.response.send_message(embeds=embeds)


# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(ListGamesCommand(bot))

