import os
import random
import sqlite3
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord import app_commands, Interaction, Embed, ui

from event_handler import schedule_game_event
from game_db_controller import *


# Bot setup
class GameBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()


bot = GameBot()


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()  # Sync all commands globally
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

    print(f"We have logged in as {bot.user}")


@bot.tree.command(name="addgame", description="Add a new game to the list.")
async def add_game(
        interaction: Interaction,
        name: str,
        min_players: int,
        max_players: int,
        steam_link: str = None,
        banner_link: str = None):

    server_id = str(interaction.guild.id)
    try:
        add_game_to_db(server_id, name, min_players, max_players, steam_link, banner_link)
        await interaction.response.send_message(f"'{name}' has been added to t’list!", ephemeral=True)
    except sqlite3.IntegrityError:
        await interaction.response.send_message("Error: Game already exists.", ephemeral=True)


@bot.tree.command(name="removegame", description="Remove a game from the list.")
async def remove_game(interaction: Interaction, name: str):
    server_id = str(interaction.guild.id)
    affected_rows = remove_game_from_db(server_id, name)
    if affected_rows > 0:
        await interaction.response.send_message(f"'{name}' has been removed.", ephemeral=True)
    else:
        await interaction.response.send_message("Error: No such game found.", ephemeral=True)


@bot.tree.command(name="listgames", description="List all games in the server.")
async def list_games(interaction: Interaction):
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
    return random.choice(games) if games else None


@bot.tree.command(name="choosegame", description="Choose a game for this week.")
async def choose_game(interaction: Interaction, player_count: int, ignore_least_played: bool = False):
    server_id = str(interaction.guild.id)

    # Fetch games based on eligibility
    games = get_eligible_games(server_id, player_count)
    if not games:
        await interaction.response.send_message(f"No games support {player_count} players!", ephemeral=True)
        return

    if not ignore_least_played:
        games = get_least_played_games(server_id, player_count)

    if not games:
        await interaction.response.send_message("No eligible games found.", ephemeral=True)
        return

    # Initial game choice
    chosen_game = pick_game(games)
    if not chosen_game:
        await interaction.response.send_message("No games available to choose from.", ephemeral=True)
        return

    embed = create_game_embed(chosen_game)

    # Interaction view with buttons
    class ConfirmChoice(ui.View):
        def __init__(self, initial_game, all_games):
            super().__init__()
            self.current_game = initial_game
            self.all_games = all_games

        @ui.button(label="Aye, we'll play this one.", style=discord.ButtonStyle.success)
        async def confirm(self, interaction: Interaction, button: ui.Button):
            log_game_selection(self.current_game[0])
            # Schedule the game event
            scheduled_event = await schedule_game_event(interaction, self.current_game)
            if scheduled_event:
                await interaction.response.edit_message(
                    content=f"Game confirmed! 🎉 Event scheduled: [View Event]({scheduled_event.url})",
                    view=None
                )
            else:
                await interaction.response.edit_message(
                    content="Game confirmed, but the event could not be scheduled.",
                    view=None
                )

        @ui.button(label="Nay, choose another.", style=discord.ButtonStyle.secondary)
        async def reject(self, interaction: Interaction, button: ui.Button):
            # Pick a different game excluding the current one
            new_game = pick_game(self.all_games, exclude_game_id=self.current_game[0])
            if not new_game:
                await interaction.response.send_message("No other eligible games available.", ephemeral=True)
                return

            # Update the current game
            self.current_game = new_game

            # Create a new embed and update the message
            new_embed = create_game_embed(new_game)
            await interaction.response.edit_message(embed=new_embed, view=self)

        @ui.button(label="Ignore least played, choose another.", style=discord.ButtonStyle.primary)
        async def ignore_least_played(self, interaction: Interaction, button: ui.Button):
            # Pick a different game but ignore the least played restriction
            new_game = pick_game(self.all_games, exclude_game_id=self.current_game[0],
                                 ignore_choosing_least_played=True)
            if not new_game:
                await interaction.response.send_message("No other eligible games available.", ephemeral=True)
                return

            # Update the current game
            self.current_game = new_game

            # Create a new embed and update the message
            new_embed = create_game_embed(new_game)
            await interaction.response.edit_message(embed=new_embed, view=self)

    await interaction.response.send_message(embed=embed, view=ConfirmChoice(chosen_game, games))

# Run the bot
initialize_database()
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
