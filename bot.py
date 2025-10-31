import asyncio
import os

import discord
from discord.ext import commands

from db import database
from db.migration_controller import run_migrations

import logging


def setup_logger():
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # quieten noisy libraries
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

    return logging.getLogger(__name__)  # root logger for your app


logger = setup_logger()


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
        logger.info(f"Synced {len(synced)} commands.")
    except Exception as e:
        logger.error(f"Error syncing commands: {e}")

    logger.info(f"We have logged in as {bot.user}")


@bot.event
async def on_application_command_error(interaction, error):
    if isinstance(error, discord.app_commands.CommandInvokeError):
        logger.error(f"Error in command '{interaction.command.name}': {error.original}")
    else:
        logger.error(f"Error in interaction: {error}")


@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    logger.error(f"An error occurred in {event}: {traceback.format_exc()}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    else:
        # Log the full traceback to the console
        logger.error(f"An error occurred: {type(error).__name__}: {error}")
        raise error  # Re-raise the error to see the traceback in logs


# Run the bot
async def main():
    async with bot:
        # Read the bot token from the environment variable
        TOKEN = os.getenv("DISCORD_BOT_TOKEN")
        if not TOKEN:
            raise EnvironmentError("DISCORD_BOT_TOKEN environment variable is missing.")

        # Migrate DB
        run_migrations()

        database.initialize_database()
        await load_cogs()
        await bot.start(TOKEN)


# Use asyncio to call the main function
asyncio.run(main())
