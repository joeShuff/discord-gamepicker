"""
Migration: Add `archived` column to game_list.

Existing rows default to 0 (not archived).
This migration is idempotent — safe to run multiple times.
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def run_migration(conn: sqlite3.Connection):
    cursor = conn.cursor()

    # Check whether the column already exists
    cursor.execute("PRAGMA table_info(game_list)")
    columns = [row[1] for row in cursor.fetchall()]

    if "archived" not in columns:
        logger.info("Migration: adding 'archived' column to game_list")
        cursor.execute(
            "ALTER TABLE game_list ADD COLUMN archived INTEGER NOT NULL DEFAULT 0"
        )
        conn.commit()
    else:
        logger.debug("Migration skipped: 'archived' column already present")