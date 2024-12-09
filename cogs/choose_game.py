import asyncio
import random

import discord
from discord import Interaction, ui, Embed
from discord.ext import commands

from event_handler import schedule_game_event
from game_db_controller import log_game_selection, get_eligible_games, get_least_played_games
from wheel_generator import generate_wheel_of_games, calculate_gif_duration


def create_wheel_for_discord(games, winning_index, filename):
    generate_wheel_of_games(games, winning_index, filename)

    # Calculate GIF duration dynamically
    gif_duration = calculate_gif_duration(filename)

    # Send the spinning wheel GIF to Discord
    with open(filename, "rb") as gif_file:
        gif_file = discord.File(gif_file, filename=filename)
        return gif_file, gif_duration


# Embed for displaying chosen game
def create_game_embed(game):
    game_id, name, steam_link, banner_link, *rest = game
    embed = Embed(title=f"Chosen Game: {name}", color=discord.Color.green())
    if steam_link:
        embed.add_field(name="Steam Link", value=steam_link, inline=False)
    if banner_link:
        embed.set_image(url=banner_link)
    return embed


# Function to choose a game randomly
def pick_game(games, exclude_game_id=None, ignore_choosing_least_played=False):
    if not ignore_choosing_least_played:
        # Filter games to include only those with the least number of times played
        # Assuming the 5th element (index 4) is the play count
        min_play_count = min(game[4] for game in games)  # Find the minimum play count
        games = [game for game in games if game[4] == min_play_count]  # Only include least played games

    # If there's only one game left in the list after filtering and it's the one we excluded, return it
    if len(games) == 1 and exclude_game_id and games[0][0] == exclude_game_id:
        return games[0]

    if exclude_game_id:
        # Filter out the game with the ID we want to exclude
        games = [game for game in games if game[0] != exclude_game_id]

    # Pick a random game from the filtered list
    if games:
        return games, random.choice(games)
    else:
        return None, None


class ConfirmChoice(ui.View):
    def __init__(self, interaction, bot, initial_game, all_games, gif_message, player_count, server_id):
        super().__init__()
        self.interaction = interaction
        self.bot = bot
        self.current_game = initial_game
        self.all_games = all_games
        self.gif_message = gif_message
        self.player_count = player_count
        self.server_id = server_id

    async def regenerate_wheel(self, interaction, exclude_game_id=None, ignore_least_played=False):
        # Fetch eligible games
        games = get_eligible_games(self.server_id, self.player_count)
        if not games:
            await interaction.followup.send("No eligible games found.", ephemeral=True)
            return None

        if not ignore_least_played:
            games = get_least_played_games(self.server_id, self.player_count)

        if not games:
            await interaction.followup.send("No eligible games found.", ephemeral=True)
            return None

        # Pick a game
        game_options, chosen_game = pick_game(games, exclude_game_id=exclude_game_id, ignore_choosing_least_played=ignore_least_played)
        if not chosen_game:
            await interaction.followup.send("No games available to choose from.", ephemeral=True)
            return None

        # Generate the GIF
        winning_index = game_options.index(chosen_game)
        file_name = "wheel_of_games.gif"
        games = [game[1] for game in game_options]
        gif_file, gif_duration = create_wheel_for_discord(games, winning_index, file_name)

        # Send the new spinning wheel GIF and remove the old one
        await self.gif_message.delete()
        new_gif_message = await interaction.followup.send(
            content="🎉 The wheel is spinning... hold tight!",
            file=gif_file,
            ephemeral=False
        )

        await asyncio.sleep(gif_duration)

        # Send the new embed with buttons
        embed = create_game_embed(chosen_game)
        new_view = ConfirmChoice(
            self.interaction, self.bot, chosen_game, game_options, new_gif_message, self.player_count, self.server_id
        )
        await interaction.followup.send(embed=embed, view=new_view)
        return chosen_game

    @ui.button(label="Aye, we'll play this one.", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        log_game_selection(self.current_game[0])
        scheduled_event = await schedule_game_event(interaction, self.current_game)
        if scheduled_event:
            await interaction.message.edit(
                content=f"Game confirmed! 🎉 Event scheduled: [View Event]({scheduled_event.url})",
                view=None
            )
        else:
            await interaction.message.edit(
                content="Game confirmed, but the event could not be scheduled.",
                view=None
            )

    @ui.button(label="Nay, choose another.", style=discord.ButtonStyle.secondary)
    async def reject(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer(thinking=True)
        await interaction.message.delete()
        await self.regenerate_wheel(interaction, exclude_game_id=self.current_game[0])

    @ui.button(label="Ignore least played, choose another.", style=discord.ButtonStyle.primary)
    async def ignore_least_played(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer(thinking=True)
        await interaction.message.delete()
        await self.regenerate_wheel(interaction, ignore_least_played=True)

    @ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        # Delete the GIF message and the current interaction message
        await self.gif_message.delete()
        await interaction.message.delete()
        await self.interaction.response.delete()
        # Send confirmation of cancellation
        await interaction.followup.send("Interaction canceled and messages cleared.", ephemeral=True)


class ChooseGameCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="choosegame", description="Choose a game to play!")
    async def choose_game(self, interaction: Interaction, player_count: int, ignore_least_played: bool = False):
        server_id = str(interaction.guild.id)

        # Fetch games
        games = get_eligible_games(server_id, player_count)
        if not games:
            await interaction.response.send_message(f"No games support {player_count} players!", ephemeral=True)
            return

        if not ignore_least_played:
            games = get_least_played_games(server_id, player_count)

        if not games:
            await interaction.response.send_message("No eligible games found.", ephemeral=True)
            return

        # Pick a game
        game_options, chosen_game = pick_game(games)
        if not chosen_game:
            await interaction.response.send_message("No games available to choose from.", ephemeral=True)
            return

        # Respond to the interaction
        await interaction.response.send_message(f"🎉 Let's get the party started! Choosing a game for {player_count} players... Please hold on while I spin the wheel! 🎮")

        # Generate the GIF
        winning_index = game_options.index(chosen_game)
        file_name = "wheel_of_games.gif"
        games = [game[1] for game in game_options]
        gif_file, gif_duration = create_wheel_for_discord(games, winning_index, file_name)

        # Send the spinning wheel GIF
        gif_message = await interaction.followup.send(
            content="🎉 The wheel is spinning... hold tight!",
            file=gif_file,
            ephemeral=False
        )

        await asyncio.sleep(gif_duration)

        # Send the embed with buttons
        embed = create_game_embed(chosen_game)
        view = ConfirmChoice(interaction, self.bot, chosen_game, game_options, gif_message, player_count, server_id)
        await interaction.followup.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(ChooseGameCommand(bot))

