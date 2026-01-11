import discord
from discord import Interaction, ui
from discord.ext import commands
from discord.ui import Button

from db.database import nuke_playcounts


# Confirmation View with Buttons
class NukeConfirmationView(ui.View):
    def __init__(self, server_id: str, requester_id: int, requester_name: str):
        super().__init__()
        self.server_id = server_id
        self.requester_id = requester_id
        self.requester_name = requester_name

    @discord.ui.button(label="Yes, nuke all playcounts", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: Interaction, button: Button):
        # Check if the presser is the requester
        if interaction.user.id == self.requester_id:
            await interaction.response.send_message("You cannot approve your own nuke request.", ephemeral=True)
            return

        # Call the function to nuke playcounts
        result = nuke_playcounts(self.server_id)

        # Acknowledge the action
        if result:
            ascii_art = """```
     _.-^^---....,,--       
 _--                  --_  
<                        >)
|                         | 
 \._                   _./  
    '''--. . , ; .--'''       
          | |   |             
       .-=||  | |=-.   
       `-=#$%&%$#=-'   
          | ;  :|     
 _____.,-#%&$@%#&#~,._____```
"""
            embed = discord.Embed(
                title="Playcounts Nuked",
                description="All playcounts have been reset to zero. The wheel will now show all games equally."
                            f"{ascii_art}",
                color=discord.Color.green()
            )
            embed.add_field(name="Requested by", value=self.requester_name, inline=True)
            embed.add_field(name="Approved by", value=interaction.user.display_name, inline=True)
            embed.set_footer(
                text=f"Executed by {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )

            # Send public message
            await interaction.response.edit_message(
                embed=embed,
                view=None
            )
        else:
            await interaction.response.edit_message(
                content="There was a problem resetting the playcounts. Please check logs and report errors or try again.",
                embed=None,
                view=None
            )

    @discord.ui.button(label="No, cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(
            content="Nuke cancelled.",
            embed=None,
            view=None
        )


class NukeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Command to nuke all playcounts
    @discord.app_commands.command(name="nuke", description="Reset all played counts to zero for a fresh wheel")
    async def nuke(self, interaction: Interaction):
        """Reset all played counts to zero, allowing the wheel to show all games equally."""
        server_id = str(interaction.guild.id)

        # Create the confirmation view
        view = NukeConfirmationView(server_id, interaction.user.id, interaction.user.display_name)

        # Send confirmation message with buttons
        embed = discord.Embed(
            title="Are you sure you want to nuke all playcounts?",
            description="This will reset the played count for all games to zero, allowing the wheel to show all games equally. Play history will be preserved but ignored. Proceed with caution. This request must be approved by another server member.",
            color=discord.Color.red()
        )
        embed.add_field(name="Requested by", value=interaction.user.display_name, inline=True)
        await interaction.response.send_message(
            embed=embed,
            view=view
        )


# Add the cog to the bot
async def setup(bot):
    await bot.add_cog(NukeCog(bot))