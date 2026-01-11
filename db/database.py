import os
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_

from db.models import Base, Game, GameWithPlayHistory, GameLog

import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.getcwd(), "config", "games.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Ensure the directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initialize_database():
    Base.metadata.create_all(bind=engine)
    logger.debug("Database initialized using SQLAlchemy.")


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def add_game_to_db(game: Game):
    with get_session() as session:
        session.add(game)
        session.commit()


def remove_game_from_db(server_id: str, name: str) -> bool:
    """Remove a game from the database. Returns True if a row was deleted."""
    with get_session() as session:
        result = session.query(Game).filter(
            and_(
                Game.server_id == server_id,
                Game.name == name
            )
        )
        if result.count() > 0:
            result.delete()
            session.commit()
            return True
        return False


def fetch_game_from_db(server_id: str, name: str) -> Optional[Game]:
    """Fetch the full Game object by server ID and name"""
    with get_session() as session:
        game = session.query(Game).filter_by(
            server_id=server_id,
            name=name
        ).first()
        return game  # Returns a Game instance or None


def fetch_game_with_memory(server_id: str, name: str) -> Optional[GameWithPlayHistory]:
    """Fetch a full game with its play history too"""
    with get_session() as session:
        game = (
            session.query(Game)
            .filter(Game.server_id == server_id)
            .filter(Game.name == name)
            .first()
        )

        if not game:
            return None

        logs = (
            session.query(GameLog.chosen_at)
            .filter(GameLog.game_id == game.id)
            .filter((GameLog.ignored.is_(None)) | (GameLog.ignored == 0))
            .order_by(GameLog.chosen_at.desc())
            .all()
        )

        play_history = [log.chosen_at for log in logs]

        return GameWithPlayHistory(
            id=game.id,
            server_id=game.server_id,
            name=game.name,
            min_players=game.min_players,
            max_players=game.max_players,
            steam_link=game.steam_link,
            banner_link=game.banner_link,
            playcount_offset=game.playcount_offset,
            play_history=play_history
        )


def get_all_server_games(server_id: str) -> List[GameWithPlayHistory]:
    """Retrieve all games for a server, including play history as a list of datetimes."""
    with get_session() as session:
        games = (
            session.query(Game)
            .filter(Game.server_id == server_id)
            .all()
        )

        game_ids = [game.id for game in games]

        # Fetch play history for all games at once
        logs = (
            session.query(GameLog.game_id, GameLog.chosen_at)
            .filter(GameLog.game_id.in_(game_ids))
            .filter((GameLog.ignored.is_(None)) | (GameLog.ignored == 0))
            .order_by(GameLog.chosen_at.desc())
            .all()
        )

        # Organize logs by game_id
        history_map: dict[int, List[datetime]] = {}
        for game_id, timestamp in logs:
            history_map.setdefault(game_id, []).append(timestamp)

        # Build result
        result = []
        for game in games:
            result.append(GameWithPlayHistory(
                id=game.id,
                server_id=game.server_id,
                name=game.name,
                min_players=game.min_players,
                max_players=game.max_players,
                steam_link=game.steam_link,
                banner_link=game.banner_link,
                playcount_offset=game.playcount_offset,
                play_history=history_map.get(game.id, [])
            ))

        return result


def get_eligible_games(server_id: str, player_count: int) -> list[GameWithPlayHistory]:
    """Retrieve games that match the player count by filtering existing server games."""
    all_games = get_all_server_games(server_id)
    return [
        game for game in all_games
        if game.min_players <= player_count <= game.max_players
    ]


def get_least_played_games(server_id: str, player_count: int) -> list[GameWithPlayHistory]:
    """Retrieve the least played games that match the player count."""
    all_games = get_all_server_games(server_id)
    eligible_games = [
        game for game in all_games
        if game.min_players <= player_count <= game.max_players
    ]
    return sorted(eligible_games, key=lambda g: len(g.play_history))


def log_game_selection(game_id: int, date: datetime = datetime.utcnow()):
    """Log the selection of a game."""
    if date is None:
        date = datetime.utcnow()

    with get_session() as session:
        new_log = GameLog(game_id=game_id, chosen_at=date)
        session.add(new_log)
        session.commit()


def mark_game_logs_as_ignored(server_id: str, game_name: str, memory_date: Optional[datetime] = None) -> bool:
    """Mark game logs as ignored. If memory_date is provided, only mark the specified timestamp; otherwise,
    mark all logs. """
    with get_session() as session:
        game = session.query(Game).filter_by(server_id=server_id, name=game_name).first()

        if not game:
            return False  # Game not found

        query = session.query(GameLog).filter(GameLog.game_id == game.id)

        if memory_date:
            query = query.filter(
                func.strftime('%Y-%m-%d %H:%M:%S', GameLog.chosen_at) ==
                memory_date.strftime('%Y-%m-%d %H:%M:%S')
            )

            matching_items = query.all()

            if len(matching_items) == 0:
                logger.debug(f"No matching plays for date {memory_date}")
                return False

        updated_count = query.update({"ignored": 1}, synchronize_session=False)
        session.commit()

        return updated_count > 0


def get_least_playcount_for_server(server_id: str) -> int:
    """
    Returns the lowest number of play history entries for any game in the server.
    If no games exist or none have play history, returns 0.
    """
    games: list[GameWithPlayHistory] = get_all_server_games(server_id)

    if not games:
        return 0

    # Get play counts
    play_counts = [(len(game.play_history) + game.playcount_offset) for game in games]

    return min(play_counts) if play_counts else 0


def edit_game_in_db(server_id: str, current_name: str, **updates) -> bool:
    """
    Edit a game's details in the database.
    Accepts keyword arguments for any editable field:
    e.g. edit_game_in_db(server_id, "Catan", name="Catan Deluxe", min_players=3)

    Returns True if an update was made, False if the game wasn't found.
    """
    editable_fields = {
        "name", "min_players", "max_players",
        "steam_link", "banner_link", "playcount_offset"
    }

    with get_session() as session:
        game = session.query(Game).filter_by(server_id=server_id, name=current_name).first()
        if not game:
            return False

        changes_made = False
        for key, value in updates.items():
            if key in editable_fields and hasattr(game, key):
                setattr(game, key, value)
                changes_made = True

        if changes_made:
            session.commit()
            return True
        else:
            return False


def nuke_playcounts(server_id: str) -> bool:
    """
    Reset all played counts for a server by marking all GameLog entries as ignored
    and resetting playcount_offset to 0 for all games.

    Returns True if any changes were made.
    """
    # Get all games for the server
    games_list = get_all_server_games(server_id)
    if not games_list:
        return False

    with get_session() as session:
        game_ids = [game.id for game in games_list]

        # Mark all GameLog entries for these games as ignored
        updated_logs = session.query(GameLog).filter(GameLog.game_id.in_(game_ids)).update({"ignored": 1}, synchronize_session=False)

        # Reset playcount_offset to 0 for all games
        updated_offsets = session.query(Game).filter(Game.server_id == server_id).update({"playcount_offset": 0}, synchronize_session=False)

        session.commit()

        return updated_logs > 0 or updated_offsets > 0
