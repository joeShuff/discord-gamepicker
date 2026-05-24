import discord
from discord import Interaction, ui, Embed
from discord.ext import commands

from db.database import remove_game_from_db, fetch_game_from_db, get_all_server_games_including_archived


class ConfirmRemove(ui.View):
    def __init__(self, requester_id: int, requester_name: str, game_name: str, banner_url: str):
        super().__init__(timeout=300)
        self.requester_id = requester_id
        self.requester_name = requester_name
        self.game_name = game_name
        self.banner_url = banner_url

    @ui.button(label="⚠️ Yes, permanently delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        if interaction.user.id == self.requester_id:
            await interaction.response.send_message(
                "You cannot approve your own removal request.", ephemeral=True
            )
            return

        server_id = str(interaction.guild.id)
        successful_removal = remove_game_from_db(server_id, self.game_name)
        if successful_removal:
            embed = Embed(
                title="🗑️ Game Permanently Deleted",
                description=f"**{self.game_name}** has been permanently removed from the game list.",
                color=discord.Color.red()
            )
            embed.add_field(name="Requested by", value=self.requester_name, inline=True)
            embed.add_field(name="Approved by", value=interaction.user.display_name, inline=True)
            if self.banner_url:
                embed.set_image(url=self.banner_url)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.edit_message(
                content="❌ This game no longer exists or was already removed.",
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

    async def on_timeout(self):
        # Public message — self.message is set after send_message() so we can edit it directly.
        for child in self.children:
            child.disabled = True
        try:
            embed = Embed(
                title="⏱️ Deletion Request Expired",
                description=f"The request to permanently delete **{self.game_name}** has expired. Run `/removegame` again if still needed.",
                color=discord.Color.dark_grey()
            )
            embed.add_field(name="Requested by", value=self.requester_name, inline=True)
            await self.message.edit(embed=embed, view=self)
        except discord.NotFound:
            pass


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

        embed = Embed(
            title="⚠️ Permanently Delete Game?",
            description=(
                f"**{interaction.user.display_name}** wants to **permanently delete** **{game_name}** from the game list.\n\n"
                "This will remove the game and **all of its play history** forever. "
                "This action **cannot be undone**.\n\n"
                "If you just want to hide the game from searches and the wheel, use `/archivegame` instead.\n\n"
                "**This request must be approved by another server member.**"
            ),
            color=discord.Color.red()
        )
        embed.add_field(name="Requested by", value=interaction.user.display_name, inline=True)
        if banner_url:
            embed.set_image(url=banner_url)

        view = ConfirmRemove(interaction.user.id, interaction.user.display_name, game_name, banner_url)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @remove_game.autocomplete("name")
    async def autocomplete_games(self, interaction: Interaction, current: str):
        """Provide autocomplete suggestions for game names (includes archived games)."""
        server_id = str(interaction.guild.id)
        games = get_all_server_games_including_archived(server_id, search=current)[:25]
        return [
            discord.app_commands.Choice(name=game.name, value=game.name)
            for game in games
        ]


# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(RemoveGameCommand(bot))