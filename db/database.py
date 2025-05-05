import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_

from db.models import Base, Game, GameWithPlayHistory, GameLog

DB_PATH = os.path.join(os.getcwd(), "config", "games.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Ensure the directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initialize_database():
    Base.metadata.create_all(bind=engine)
    print("Database initialized using SQLAlchemy.")


def get_session():
    return SessionLocal()


def add_game_to_db(game: Game):
    session = get_session()
    try:
        session.add(game)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def remove_game_from_db(server_id: str, name: str) -> bool:
    """Remove a game from the database. Returns True if a row was deleted."""
    session = SessionLocal()
    try:
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
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def fetch_game_from_db(server_id: str, name: str) -> Optional[Game]:
    """Fetch the full Game object by server ID and name"""
    session = SessionLocal()
    try:
        game = session.query(Game).filter_by(
            server_id=server_id,
            name=name
        ).first()
        return game  # Returns a Game instance or None
    finally:
        session.close()


def get_all_server_games(server_id: str) -> List[GameWithPlayHistory]:
    """Retrieve all games for a server, including play history as a list of datetimes."""
    session = SessionLocal()
    try:
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
            .order_by(GameLog.chosen_at.asc())
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
                play_history=history_map.get(game.id, [])
            ))

        return result
    finally:
        session.close()


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
