import discord
from discord import Interaction, ui, Embed
from discord.ext import commands

from db.database import remove_game_from_db, fetch_game_from_db
from game_db_controller import get_all_games_display, fetch_game_names


class ConfirmRemove(ui.View):
    def __init__(self, interaction: Interaction, game_name: str, banner_url: str):
        super().__init__()
        self.interaction = interaction
        self.game_name = game_name
        self.banner_url = banner_url

    @ui.button(label="Yes, remove", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        server_id = str(interaction.guild.id)
        successful_removal = remove_game_from_db(server_id, self.game_name)
        if successful_removal:
            await interaction.response.edit_message(
                content=f"'{self.game_name}' has been successfully removed.",
                embed=None,
                view=None
            )
        else:
            await interaction.response.edit_message(
                content="Error: No such game found.",
                embed=None,
                view=None
            )

    @ui.button(label="No, cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        await interaction.response.edit_message(
            content="Game removal canceled.",
            embed=None,
            view=None
        )


class RemoveGameCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="removegame", description="Remove a game from the list.")
    async def remove_game(self, interaction: Interaction, name: str):
        server_id = str(interaction.guild.id)

        # Fetch game details from the database (replace this with your actual query)
        game = fetch_game_from_db(server_id, name)
        if game is None:
            await interaction.response.send_message("Error: No such game found.", ephemeral=True)
            return

        game_name = game.name
        banner_url = game.banner_link

        # Create an embed for confirmation
        embed = Embed(title="Confirm Game Removal", description=f"Are you sure you want to remove **{game_name}**?")
        if banner_url:
            embed.set_image(url=banner_url)

        # Send the embed with confirmation buttons
        view = ConfirmRemove(interaction, game_name, banner_url)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @remove_game.autocomplete("name")
    async def autocomplete_games(self, interaction: Interaction, current: str):
        """Provide autocomplete suggestions for game names."""
        server_id = str(interaction.guild.id)
        game_names = fetch_game_names(server_id)  # Fetch a list of game names from the database

        return [
            discord.app_commands.Choice(name=game, value=game)
            for game in game_names if current.lower() in game.lower()
        ]


# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(RemoveGameCommand(bot))
