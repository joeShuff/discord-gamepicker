import asyncio
import os

import discord
from discord.ext import commands

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

# Load all cogs from the `cogs` directory
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"cogs.{filename[:-3]}")


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()  # Sync all commands globally
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

    print(f"We have logged in as {bot.user}")


@bot.event
async def on_application_command_error(interaction, error):
    if isinstance(error, discord.app_commands.CommandInvokeError):
        print(f"Error in command '{interaction.command.name}': {error.original}")
    else:
        print(f"Error in interaction: {error}")


@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    print(f"An error occurred in {event}: {traceback.format_exc()}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    else:
        # Log the full traceback to the console
        print(f"An error occurred: {type(error).__name__}: {error}")
        raise error  # Re-raise the error to see the traceback in logs


# Run the bot
async def main():
    async with bot:
        # Read the bot token from the environment variable
        TOKEN = os.getenv("DISCORD_BOT_TOKEN")
        if not TOKEN:
            raise EnvironmentError("DISCORD_BOT_TOKEN environment variable is missing.")

        initialize_database()
        await load_cogs()
        await bot.start(TOKEN)


# Use asyncio to call the main function
asyncio.run(main())
