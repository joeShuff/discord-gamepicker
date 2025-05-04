import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_

from db.models import Base, Game

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


def fetch_game_from_db(server_id: str, name: str) -> Game:
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

