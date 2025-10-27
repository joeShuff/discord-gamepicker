import logging
import os


def setup_logger():
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Optional: quiet noisy libraries
    logging.getLogger("discord").setLevel(logging.WARNING)

    return logging.getLogger("discord_gamebot")  # root logger for your app


logger = setup_logger()
