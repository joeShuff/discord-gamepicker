"""
Migration: Add `repeat` column to game_log.

Existing rows are normal game selections, so they default to 0/False.
This migration is idempotent.
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def run_migration(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(game_log)")
    columns = [row[1] for row in cursor.fetchall()]

    if "repeat" not in columns:
        logger.info("Migration: adding 'repeat' column to game_log")
        cursor.execute(
            "ALTER TABLE game_log ADD COLUMN repeat INTEGER NOT NULL DEFAULT 0"
        )
        conn.commit()
    else:
        logger.debug("Migration skipped: 'repeat' column already present")