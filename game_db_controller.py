import sqlite3

DB_PATH = "games.db"

def initialize_database():
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
            LEFT JOIN game_log ON game_list.id = game_log.game_id
            WHERE game_list.server_id = ?
            GROUP BY game_list.id
            ORDER BY last_played ASC NULLS FIRST
        """, (server_id,))
        return cursor.fetchall()


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
            SELECT game_list.id, game_list.name, game_list.steam_link, game_list.banner_link, COUNT(game_log.id) AS times_played
            FROM game_list
            LEFT JOIN game_log ON game_list.id = game_log.game_id
            WHERE game_list.server_id = ? AND game_list.min_players <= ? AND game_list.max_players >= ?
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
