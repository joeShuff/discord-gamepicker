import asyncio
import random
from typing import List

import discord
from discord import Interaction, ui, Embed
from discord.ext import commands
import logging

from ai_responses import generate_response
from db.database import get_eligible_games, get_least_played_games, get_all_server_games, \
    log_game_selection, fetch_game_with_memory
from db.models import GameWithPlayHistory
from event_handler import schedule_game_event
from util import date_util
import wheel_generator
import wheel_generator_legacy

logger = logging.getLogger(__name__)

def create_wheel_for_discord(games: List[str], winning_index: int, filename: str, legacy: bool = False) -> tuple[discord.File, int]:
    if legacy:
        wheel_generator_legacy.generate_wheel_of_games(games, winning_index, filename)
        gif_duration = wheel_generator_legacy.calculate_gif_duration(filename)
    else:
        wheel_generator.generate_wheel_of_games(games, winning_index, filename)
        gif_duration = wheel_generator.calculate_gif_duration(filename)

    # Send the spinning wheel GIF to Discord
    with open(filename, "rb") as gif_file:
        gif_file = discord.File(gif_file, filename=filename)
        return gif_file, gif_duration


# Embed for displaying chosen game
def create_game_embed(game: GameWithPlayHistory):
    embed = Embed(title=f"Chosen Game: {game.name}", color=discord.Color.green())
    embed.add_field(name="Supported players", value=f"{game.min_players} - {game.max_players}", inline=False)
    if game.steam_link:
        embed.add_field(name="Steam Link", value=game.steam_link, inline=False)
    if game.banner_link:
        embed.set_image(url=game.banner_link)
    return embed


# Function to choose a game randomly
def pick_game(games: List[GameWithPlayHistory], exclude_game_id: str = None, ignore_least_played_bias=False) -> \
        tuple[List[GameWithPlayHistory], GameWithPlayHistory]:
    if not ignore_least_played_bias:
        # Filter games to include only those with the least  number of times played
        min_play_count = min(
            len(game.play_history) + game.playcount_offset for game in games)  # Find the minimum play count
        games = [game for game in games if
                 (len(game.play_history) + game.playcount_offset) == min_play_count]  # Only include least played games

    # If there's only one game left in the list after filtering, and it's the one we excluded, return it
    if len(games) == 1 and exclude_game_id and games[0].id == exclude_game_id:
        return games, games[0]

    if exclude_game_id:
        # Filter out the game with the ID we want to exclude
        games = [game for game in games if game.id != exclude_game_id]

    # Pick a random game from the filtered list
    if games:
        return games, random.choice(games)
    else:
        return None, None


class ConfirmChoice(ui.View):
    def __init__(self, interaction, bot, initial_game, all_games, gif_message, player_count, server_id, event_day=None, legacy_wheel=False):
        super().__init__(timeout=300)
        self.interaction = interaction
        self.bot = bot
        self.current_game = initial_game
        self.all_games = all_games
        self.gif_message = gif_message
        self.player_count = player_count
        self.server_id = server_id
        self.event_day = event_day
        self.legacy_wheel = legacy_wheel

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
        game_options, chosen_game = pick_game(games, exclude_game_id=exclude_game_id,
                                              ignore_least_played_bias=ignore_least_played)
        if not chosen_game:
            await interaction.followup.send("No games available to choose from.", ephemeral=True)
            return None

        # Generate the GIF
        winning_index = game_options.index(chosen_game)
        file_name = "wheel_of_games.gif"
        game_names = [game.name for game in game_options]
        gif_file, gif_duration = create_wheel_for_discord(game_names, winning_index, file_name, legacy=self.legacy_wheel)

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
            self.interaction, self.bot, chosen_game, game_options, new_gif_message, self.player_count, self.server_id,
            self.event_day, legacy_wheel=self.legacy_wheel
        )
        await interaction.followup.send(embed=embed, view=new_view)
        return chosen_game

    @ui.button(label="Aye, we'll play this one.", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        # Immediately remove ability to click on the message because this can lead to double presses
        await interaction.edit_original_response(content="Reyt, sorting t'event out...", view=None, embed=None)
        await interaction.response.defer()

        scheduled_event, event_date = await schedule_game_event(interaction, self.current_game, self.event_day)

        log_game_selection(self.current_game.id, event_date)

        if scheduled_event is not None:
            confirm_msg = await generate_response(
                "The group have confirmed their game choice and an event has been scheduled.",
                f"Game: {self.current_game.name}. Event link: {scheduled_event.url}"
            ) or f"Game confirmed! 🎉 [View Event]({scheduled_event.url})"
            if scheduled_event.url not in confirm_msg:
                confirm_msg += f" [View Event]({scheduled_event.url})"
            await interaction.edit_original_response(content=confirm_msg, view=None, embed=None)
        else:
            confirm_msg = await generate_response(
                "The group confirmed their game but the Discord event could not be scheduled.",
                f"Game: {self.current_game.name}"
            ) or "Game confirmed, but the event could not be scheduled."
            await interaction.edit_original_response(content=confirm_msg, view=None)
        self.stop()

    @ui.button(label="Nay, choose another.", style=discord.ButtonStyle.secondary)
    async def reject(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer()

        try:
            reroll_msg = await generate_response(
                "Someone rejected the chosen game and wants a different one.",
                f"Rejected game: {self.current_game.name}"
            ) or "Nay bother, let's have another go..."
            await self.gif_message.edit(content=reroll_msg, attachments=[])
            await interaction.message.delete()
            await self.regenerate_wheel(self.interaction, exclude_game_id=self.current_game.id)
        except Exception as e:
            logger.error("Something went wrong when rejecting a game choice. See exception.")
            logger.error(e)

    @ui.button(label="Ignore least played, choose another.", style=discord.ButtonStyle.primary)
    async def ignore_least_played(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer()

        try:
            reroll_msg = await generate_response(
                "Someone wants to ignore the least-played weighting and pick any game at random."
            ) or "Reyt, we'll pick from t'lot this time..."
            await self.gif_message.edit(content=reroll_msg, attachments=[])
            await interaction.message.delete()
            await self.regenerate_wheel(self.interaction, ignore_least_played=True)
        except Exception as e:
            logger.error("Something went wrong when rejecting a game choice. See exception.")
            logger.error(e)

    @ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        await interaction.response.defer()

        # Delete the GIF message and the current interaction message
        await self.gif_message.delete()
        cancel_msg = await generate_response(
            "The user cancelled the game selection entirely."
        ) or "Reet then, nowt chosen. Give 'er another spin whenever tha's ready!"
        await interaction.edit_original_response(content=cancel_msg, view=None, embed=None)
        self.stop()

    async def on_timeout(self):
        # Public message — self.message is the result card followup, stored after send so we edit only that message.
        for child in self.children:
            child.disabled = True
        try:
            embed = Embed(
                title="⏱️ Game Selection Expired",
                description=f"The selection for **{self.current_game.name}** has expired. Run `/choosegame` again to spin the wheel.",
                color=discord.Color.dark_grey()
            )
            embed.add_field(name="Players", value=str(self.player_count), inline=True)
            timeout_msg = await generate_response(
                "The game selection timed out because nobody confirmed or cancelled in time.",
                f"Game that was shown: {self.current_game.name}"
            ) or "Tha took too long! Run `/choosegame` again when tha's ready."
            embed.description = embed.description + "\n\n" + timeout_msg
            await self.message.edit(embed=embed, view=self)
        except (discord.NotFound, Exception):
            pass


class ChooseGameCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="choosegame", description="Choose a game to play!")
    @discord.app_commands.describe(
        player_count="Number of players — only games that support this count will be eligible.",
        ignore_least_played="If true, picks from all eligible games instead of only the least played ones.",
        event_day="Schedule the event on a specific day (format: dd/MMM, e.g. 18/Dec). Leave blank for no event.",
        force_game="Force a specific game to be selected regardless of play count or eligibility.",
        legacy_wheel="Use the original wheel style instead of the new one.",
    )
    async def choose_game(
            self,
            interaction: Interaction,
            player_count: int,
            ignore_least_played: bool = False,
            event_day: str = None,
            force_game: str = None,
            legacy_wheel: bool = False
    ):
        server_id = str(interaction.guild.id)

        if event_day:
            try:
                date_util.check_valid_input_date(event_day)
            except ValueError:
                await interaction.response.send_message(
                    f"Invalid date format for `event_day`: `{event_day}`. Please use the format `dd/MMM` (e.g., `18/Dec`).",
                    ephemeral=True
                )
                return

        # Fetch games
        games = get_eligible_games(server_id, player_count)

        if not ignore_least_played:
            games = get_least_played_games(server_id, player_count)

        if len(games) > 25:
            logger.info(f"Reducing games to 25, currently it is {len(games)}")
            games = random.sample(games, 25)

        if not games:
            await interaction.response.send_message(f"No games support {player_count} players!", ephemeral=True)
            return

        # Pick a game
        game_options, chosen_game = pick_game(games, ignore_least_played_bias=ignore_least_played)

        if force_game:
            matching_game = fetch_game_with_memory(server_id, force_game)

            if matching_game is None:
                await interaction.response.send_message(
                    f"The specified game `{force_game}` was not found.",
                    ephemeral=True,
                )
                return

            if matching_game not in game_options:
                logger.debug(f"forced game {force_game} isn't in options list, adding it")
                game_options.append(matching_game)

            chosen_game = matching_game

        if not chosen_game:
            await interaction.response.send_message("No games available to choose from.", ephemeral=True)
            return

        # Defer the response to show "thinking" and get up to 15 minutes to respond
        await interaction.response.defer()

        # Generate AI response for the spin message
        spin_msg = await generate_response(
            "The bot is about to spin the wheel to pick a game for the group to play.",
            f"{player_count} players are joining."
        ) or f"🎉 Let's get the party started! Choosing a game for {player_count} players... Please hold on while I spin the wheel! 🎮"
        await interaction.followup.send(spin_msg)

        # Generate the GIF
        winning_index = game_options.index(chosen_game)
        file_name = "wheel_of_games.gif"
        games = [game.name for game in game_options]
        gif_file, gif_duration = create_wheel_for_discord(games, winning_index, file_name, legacy=legacy_wheel)

        # Send the spinning wheel GIF
        gif_message = await interaction.followup.send(
            content="🎉 The wheel is spinning... hold tight!",
            file=gif_file,
            ephemeral=False
        )

        await asyncio.sleep(gif_duration)

        # Send the embed with buttons
        embed = create_game_embed(chosen_game)
        view = ConfirmChoice(interaction, self.bot, chosen_game, game_options, gif_message, player_count, server_id,
                             event_day, legacy_wheel=legacy_wheel)
        view.message = await interaction.followup.send(embed=embed, view=view)

    @choose_game.autocomplete("event_day")
    async def autocomplete_event_day(self, interaction: Interaction, current: str):
        """
        Autocomplete for the event_day parameter to suggest the next 4 Wednesdays.
        """
        suggestions = date_util.get_next_wednesdays(4)

        # Create Choices for autocomplete
        return [
            discord.app_commands.Choice(name=f"{suggestion}", value=suggestion)
            for suggestion in suggestions
        ]

    @choose_game.autocomplete(name="force_game")
    async def autocomplete_force_game(self, interaction: Interaction, current: str):
        """Provide autocomplete suggestions for game names."""
        server_id = str(interaction.guild.id)
        game_names = get_all_server_games(server_id, search=current)[:25]  # Fetch a list of game names from the database

        return [
            discord.app_commands.Choice(name=game.name, value=game.name)
            for game in game_names
        ]


async def setup(bot):
    await bot.add_cog(ChooseGameCommand(bot))