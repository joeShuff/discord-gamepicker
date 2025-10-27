import importlib
import os
import sqlite3

from db.database import DB_PATH
import logging
logger = logging.getLogger(__name__)

def get_migration_modules():
    migration_dir = os.getcwd() + "/db/migrations"
    files = sorted(f for f in os.listdir(migration_dir) if f.endswith(".py") and f[0:3].isdigit())

    for file in files:
        module_name = f"db.migrations.{file[:-3]}"
        yield importlib.import_module(module_name)


def run_migrations():
    conn = sqlite3.connect(DB_PATH)
    try:
        for module in get_migration_modules():
            logger.debug(f"Running {module.__name__}")
            module.run_migration(conn)
    finally:
        conn.close()

