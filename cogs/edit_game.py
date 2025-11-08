import discord
from discord import Interaction, ui, Embed
from discord.ext import commands

from db.database import fetch_game_from_db, edit_game_in_db, get_all_server_games


class ConfirmEdit(ui.View):
    def __init__(self, interaction: Interaction, game_name: str, updates: dict, old_values: dict, banner_url: str):
        super().__init__()
        self.interaction = interaction
        self.game_name = game_name
        self.updates = updates
        self.old_values = old_values
        self.banner_url = banner_url

    @ui.button(label="Yes, save changes", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        server_id = str(interaction.guild.id)
        success = edit_game_in_db(server_id, self.game_name, **self.updates)

        if success:
            # Build summary embed for public announcement
            embed = Embed(
                title=f"Game Updated: {self.updates.get('name', self.game_name)}",
                description=f"'{self.game_name}' has been updated!",
                color=discord.Color.green()
            )

            # Add changed fields
            for key, new_value in self.updates.items():
                old_value = self.old_values.get(key, None)
                embed.add_field(
                    name=key.replace('_', ' ').title(),
                    value=f"**Before:** {old_value if old_value is not None else 'N/A'}\n"
                          f"**After:** {new_value}",
                    inline=False
                )

            # Use new banner if provided, else old one
            banner_to_show = self.updates.get("banner_link", self.banner_url)
            if banner_to_show:
                embed.set_image(url=banner_to_show)

            embed.set_footer(
                text=f"Edited by {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )

            # Public message in the same channel
            await interaction.channel.send(embed=embed)

            await interaction.response.edit_message(
                content=f"Reyt, '{self.game_name}' has been updated successfully!",
                embed=None,
                view=None
            )
        else:
            await interaction.response.edit_message(
                content="Couldn’t update that game — might not exist anymore.",
                embed=None,
                view=None
            )

    @ui.button(label="No, cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        await interaction.response.edit_message(
            content="Edit cancelled — nowt changed.",
            embed=None,
            view=None
        )


class EditGameCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="editgame", description="Edit details of an existing game.")
    async def edit_game(
        self,
        interaction: Interaction,
        name: str,
        new_name: str = None,
        min_players: int = None,
        max_players: int = None,
        steam_link: str = None,
        banner_link: str = None,
    ):
        server_id = str(interaction.guild.id)
        game = fetch_game_from_db(server_id, name)

        if not game:
            await interaction.response.send_message("Error: No such game found.", ephemeral=True)
            return

        updates = {
            "name": new_name,
            "min_players": min_players,
            "max_players": max_players,
            "steam_link": steam_link,
            "banner_link": banner_link,
        }
        updates = {k: v for k, v in updates.items() if v is not None}

        if not updates:
            await interaction.response.send_message("Ey up, you’ve not told me what to change!", ephemeral=True)
            return

        # Build summary embed
        embed = Embed(
            title=f"Confirm Edit for '{game.name}'",
            description="Here’s what’ll be changed if you confirm:",
            color=discord.Color.blurple()
        )

        # Show only changed fields
        for key, new_value in updates.items():
            old_value = getattr(game, key, None)
            embed.add_field(
                name=key.replace("_", " ").title(),
                value=f"**Current:** {old_value if old_value is not None else 'N/A'}\n"
                      f"**New:** {new_value}",
                inline=False
            )

        if "banner_link" in updates.keys():
            embed.set_image(url=updates.get("banner_link"))
        elif game.banner_link:
            embed.set_image(url=game.banner_link)

        # Send the embed with confirmation buttons
        view = ConfirmEdit(interaction, game.name, updates, game.__dict__, game.banner_link)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @edit_game.autocomplete("name")
    async def autocomplete_games(self, interaction: Interaction, current: str):
        """Provide autocomplete suggestions for game names."""
        server_id = str(interaction.guild.id)
        game_names = get_all_server_games(server_id)

        return [
            discord.app_commands.Choice(name=game.name, value=game.name)
            for game in game_names if current.lower() in game.name.lower()
        ]


# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(EditGameCommand(bot))
