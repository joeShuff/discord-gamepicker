import sqlite3
import os

DB_PATH = os.path.join(os.getcwd(), "config", "games.db")

def initialize_database():
    # Ensure the directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    """Initializes the SQLite database with the required tables if they don't already exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create the `game_list` table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS game_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        server_id TEXT NOT NULL,
        name TEXT NOT NULL,
        steam_link TEXT,
        min_players INTEGER NOT NULL,
        max_players INTEGER NOT NULL,
        banner_link TEXT
    )
    """)

    # Create the `game_log` table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS game_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id INTEGER NOT NULL,
        chosen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ignored BOOLEAN DEFAULT 0,
        FOREIGN KEY (game_id) REFERENCES game_list(id)
    )
    """)

    conn.commit()
    conn.close()
    print("Database initialized (or already exists).")


def db_connect():
    """Connect to the SQLite database."""
    return sqlite3.connect(DB_PATH)


def add_game_to_db(server_id, name, min_players, max_players, steam_link=None, banner_link=None):
    """Add a game to the database."""
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO game_list (server_id, name, min_players, max_players, steam_link, banner_link)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (server_id, name, min_players, max_players, steam_link, banner_link),
        )


def remove_game_from_db(server_id, name):
    """Remove a game from the database."""
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM game_list WHERE server_id = ? AND name = ?", (server_id, name)
        )
        return cursor.rowcount  # Returns the number of rows affected


def fetch_game_from_db(server_id, name):
    # Query the database to find the game
    with db_connect() as conn:
        cursor = conn.cursor()
        query = "SELECT name, banner_link FROM game_list WHERE server_id = ? AND name = ?"
        return cursor.execute(query, (server_id, name)).fetchone()


def get_all_games(server_id):
    """Retrieve all games for a server."""
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                game_list.name, 
                MAX(game_log.chosen_at) AS last_played, 
                COUNT(game_log.id) AS times_played
            FROM game_list
            LEFT JOIN game_log 
                ON game_list.id = game_log.game_id 
                AND (game_log.ignored IS NULL OR game_log.ignored = 0)
            WHERE game_list.server_id = ?
            GROUP BY game_list.id
            ORDER BY last_played ASC NULLS FIRST
        """, (server_id,))
        return cursor.fetchall()


def fetch_game_names(server_id):
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM game_list
            WHERE server_id = ?
        """, (server_id,))
        return [row[0] for row in cursor.fetchall()]


def get_eligible_games(server_id, player_count):
    """Retrieve games that match the player count."""
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, steam_link, banner_link
            FROM game_list
            WHERE server_id = ? AND min_players <= ? AND max_players >= ?
        """, (server_id, player_count, player_count))
        return cursor.fetchall()


def get_least_played_games(server_id, player_count):
    """Retrieve the least played games that match the player count."""
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT game_list.id, game_list.name, game_list.steam_link, game_list.banner_link, 
                   COUNT(game_log.id) AS times_played
            FROM game_list
            LEFT JOIN game_log 
                ON game_list.id = game_log.game_id 
                AND (game_log.ignored IS NULL OR game_log.ignored = 0)
            WHERE game_list.server_id = ? 
              AND game_list.min_players <= ? 
              AND game_list.max_players >= ?
            GROUP BY game_list.id
            ORDER BY times_played ASC
        """, (server_id, player_count, player_count))
        return cursor.fetchall()


def log_game_selection(game_id):
    """Log the selection of a game."""
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO game_log (game_id) VALUES (?)", (game_id,)
        )


def mark_game_logs_as_ignored(server_id, game_name, memory_date=None):
    """Mark game logs as ignored. If memory_date is provided, only mark the specified timestamp; otherwise, mark all logs."""
    with db_connect() as conn:
        cursor = conn.cursor()

        # Fetch the game_id from the game_list table using the game name
        cursor.execute("""
            SELECT id FROM game_list WHERE name = ? AND server_id = ?
        """, (game_name, server_id))
        result = cursor.fetchone()

        if result:
            game_id = result[0]

            # If memory_date is provided, only update the log for that specific timestamp
            if memory_date:
                cursor.execute("""
                    UPDATE game_log
                    SET ignored = 1
                    WHERE game_id = ? AND chosen_at = ?
                """, (game_id, memory_date))
            else:
                # If no memory_date is provided, update all logs for that game
                cursor.execute("""
                    UPDATE game_log
                    SET ignored = 1
                    WHERE game_id = ?
                """, (game_id,))

            conn.commit()
            return True  # Indicating the game logs were marked as ignored
        else:
            return False  # Game not found in game_list



def fetch_log_dates_for_game(server_id, game_name):
    """Fetch timestamps for logs associated with a specific game that are not ignored."""
    with db_connect() as conn:
        cursor = conn.cursor()

        # Fetch the log timestamps for the specified game, excluding ignored entries
        cursor.execute("""
            SELECT DISTINCT chosen_at AS log_timestamp
            FROM game_log
            JOIN game_list ON game_log.game_id = game_list.id
            WHERE game_list.server_id = ? 
              AND game_list.name = ?
              AND (game_log.ignored IS NULL OR game_log.ignored = 0)
            ORDER BY log_timestamp DESC
        """, (server_id, game_name))

        return [row[0] for row in cursor.fetchall()]  # List of timestamps


def get_games_by_player_count(server_id, player_count):
    """Fetch games that support the specified player count."""
    with db_connect() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                        SELECT 
                            game_list.name, 
                            MAX(game_log.chosen_at) AS last_played, 
                            COUNT(game_log.id) AS times_played
                        FROM game_list
                        LEFT JOIN game_log 
                            ON game_list.id = game_log.game_id 
                            AND (game_log.ignored IS NULL OR game_log.ignored = 0)
                        WHERE game_list.server_id = ? 
                        AND game_list.min_players <= ? 
                        AND game_list.max_players >= ?
                        GROUP BY game_list.id
                        ORDER BY last_played ASC NULLS FIRST
                    """, (server_id, player_count, player_count))
        return cursor.fetchall()

