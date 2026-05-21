import discord
from discord import Interaction, ui, Embed
from discord.ext import commands

from db.database import (
    archive_game_in_db,
    unarchive_game_in_db,
    fetch_game_from_db,
    get_all_server_games,
    get_archived_server_games,
)


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

class ConfirmArchive(ui.View):
    def __init__(self, interaction: Interaction, game_name: str):
        super().__init__(timeout=300)
        self.original_interaction = interaction
        self.game_name = game_name

    @ui.button(label="Yes, archive it", style=discord.ButtonStyle.primary)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        server_id = str(interaction.guild.id)
        success = archive_game_in_db(server_id, self.game_name)
        await interaction.response.defer(ephemeral=True)
        if success:
            await self.original_interaction.delete_original_response()
            await interaction.channel.send(
                f"📦 **{self.game_name}** has been archived by {interaction.user.mention} "
                f"and will no longer appear in searches or wheel spins."
            )
        else:
            await self.original_interaction.edit_original_response(
                content="❌ This game no longer exists or was already removed.",
                embed=None,
                view=None
            )

    @ui.button(label="No, cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        await interaction.response.edit_message(
            content="Archive cancelled. No changes were made.",
            embed=None,
            view=None
        )

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            embed = Embed(
                title="⏱️ Archive Request Expired",
                description=f"The request to archive **{self.game_name}** has expired. Run `/archivegame` again if still needed.",
                color=discord.Color.dark_grey()
            )
            await self.original_interaction.edit_original_response(embed=embed, view=self)
        except discord.NotFound:
            pass


# ---------------------------------------------------------------------------
# Unarchive
# ---------------------------------------------------------------------------

class ConfirmUnarchive(ui.View):
    def __init__(self, interaction: Interaction, game_name: str):
        super().__init__(timeout=300)
        self.original_interaction = interaction
        self.game_name = game_name

    @ui.button(label="Yes, unarchive it", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        server_id = str(interaction.guild.id)
        success = unarchive_game_in_db(server_id, self.game_name)
        await interaction.response.defer(ephemeral=True)
        if success:
            await self.original_interaction.delete_original_response()
            await interaction.channel.send(
                f"✅ **{self.game_name}** has been unarchived by {interaction.user.mention} "
                f"and will appear in searches and wheel spins again."
            )
        else:
            await self.original_interaction.edit_original_response(
                content="❌ This game no longer exists or was already removed.",
                embed=None,
                view=None
            )


    @ui.button(label="No, cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        await interaction.response.edit_message(
            content="Unarchive cancelled. No changes were made.",
            embed=None,
            view=None
        )

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            embed = Embed(
                title="⏱️ Unarchive Request Expired",
                description=f"The request to unarchive **{self.game_name}** has expired. Run `/unarchivegame` again if still needed.",
                color=discord.Color.dark_grey()
            )
            await self.original_interaction.edit_original_response(embed=embed, view=self)
        except discord.NotFound:
            pass


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class ArchiveGameCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- /archivegame ---

    @discord.app_commands.command(
        name="archivegame",
        description="Archive a game so it won't appear in searches or wheel spins (but isn't deleted)."
    )
    async def archive_game(self, interaction: Interaction, name: str):
        server_id = str(interaction.guild.id)

        game = fetch_game_from_db(server_id, name)
        if game is None:
            await interaction.response.send_message("❌ Error: No such game found.", ephemeral=True)
            return

        if game.archived:
            await interaction.response.send_message(
                f"**{game.name}** is already archived. Use `/unarchivegame` to restore it.",
                ephemeral=True
            )
            return

        embed = Embed(
            title="📦 Archive Game?",
            description=(
                f"Archiving **{game.name}** will hide it from searches and wheel spins.\n\n"
                "Its play history will be preserved and you can restore it at any time with `/unarchivegame`."
            ),
            color=discord.Color.blurple()
        )
        if game.banner_link:
            embed.set_image(url=game.banner_link)

        view = ConfirmArchive(interaction, game.name)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @archive_game.autocomplete("name")
    async def autocomplete_active_games(self, interaction: Interaction, current: str):
        """Autocomplete from non-archived games only."""
        server_id = str(interaction.guild.id)
        games = get_all_server_games(server_id, search=current)[:25]
        return [
            discord.app_commands.Choice(name=game.name, value=game.name)
            for game in games
        ]

    # --- /unarchivegame ---

    @discord.app_commands.command(
        name="unarchivegame",
        description="Restore an archived game so it appears in searches and wheel spins again."
    )
    async def unarchive_game(self, interaction: Interaction, name: str):
        server_id = str(interaction.guild.id)

        game = fetch_game_from_db(server_id, name)
        if game is None:
            await interaction.response.send_message("❌ Error: No such game found.", ephemeral=True)
            return

        if not game.archived:
            await interaction.response.send_message(
                f"**{game.name}** is not archived. Use `/archivegame` to archive it.",
                ephemeral=True
            )
            return

        embed = Embed(
            title="✅ Unarchive Game?",
            description=(
                f"Restoring **{game.name}** will make it visible in searches and wheel spins again."
            ),
            color=discord.Color.green()
        )
        if game.banner_link:
            embed.set_image(url=game.banner_link)

        view = ConfirmUnarchive(interaction, game.name)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @unarchive_game.autocomplete("name")
    async def autocomplete_archived_games(self, interaction: Interaction, current: str):
        """Autocomplete from archived games only."""
        server_id = str(interaction.guild.id)
        games = get_archived_server_games(server_id, search=current)[:25]
        return [
            discord.app_commands.Choice(name=game.name, value=game.name)
            for game in games
        ]


# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(ArchiveGameCommand(bot))