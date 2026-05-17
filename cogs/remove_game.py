import discord
from discord import Interaction, ui, Embed
from discord.ext import commands

from db.database import remove_game_from_db, fetch_game_from_db, get_all_server_games_including_archived


class ConfirmRemove(ui.View):
    def __init__(self, interaction: Interaction, game_name: str, banner_url: str):
        super().__init__()
        self.interaction = interaction
        self.game_name = game_name
        self.banner_url = banner_url

    @ui.button(label="⚠️ Yes, permanently delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        server_id = str(interaction.guild.id)
        successful_removal = remove_game_from_db(server_id, self.game_name)
        if successful_removal:
            # Update the private confirmation message
            await interaction.response.edit_message(
                content=f"✅ **{self.game_name}** has been permanently deleted.",
                embed=None,
                view=None
            )
            # Send a public message so the channel knows
            await interaction.channel.send(
                f"🗑️ **{self.game_name}** has been permanently removed from the game list by {interaction.user.mention}."
            )
        else:
            await interaction.response.edit_message(
                content="❌ Error: No such game found.",
                embed=None,
                view=None
            )

    @ui.button(label="No, cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        await interaction.response.edit_message(
            content="Game removal cancelled. No changes were made.",
            embed=None,
            view=None
        )


class RemoveGameCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="removegame", description="Permanently delete a game from the list.")
    async def remove_game(self, interaction: Interaction, name: str):
        server_id = str(interaction.guild.id)

        game = fetch_game_from_db(server_id, name)
        if game is None:
            await interaction.response.send_message("❌ Error: No such game found.", ephemeral=True)
            return

        game_name = game.name
        banner_url = game.banner_link

        # Make the destructive nature very clear in the confirmation embed
        embed = Embed(
            title="⚠️ Permanently Delete Game?",
            description=(
                f"You are about to **permanently delete** **{game_name}** from the game list.\n\n"
                "This will remove the game and **all of its play history** forever. "
                "This action **cannot be undone**.\n\n"
                "If you just want to hide the game from searches and the wheel, use `/archivegame` instead."
            ),
            color=discord.Color.red()
        )
        if banner_url:
            embed.set_image(url=banner_url)

        view = ConfirmRemove(interaction, game_name, banner_url)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @remove_game.autocomplete("name")
    async def autocomplete_games(self, interaction: Interaction, current: str):
        """Provide autocomplete suggestions for game names (includes archived games)."""
        server_id = str(interaction.guild.id)
        game_names = get_all_server_games_including_archived(server_id)[:25]

        return [
            discord.app_commands.Choice(name=game.name, value=game.name)
            for game in game_names if current.lower() in game.name.lower()
        ]


# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(RemoveGameCommand(bot))