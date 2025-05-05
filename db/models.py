from dataclasses import dataclass
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


@dataclass
class GameWithPlayHistory:
    id: int
    server_id: str
    name: str
    min_players: int
    max_players: int
    steam_link: Optional[str]
    banner_link: Optional[str]
    play_history: List[datetime]

    def __eq__(self, other):
        if not isinstance(other, GameWithPlayHistory):
            return NotImplemented
        return (
                self.id == other.id
        )


class Game(Base):
    __tablename__ = "game_list"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    steam_link = Column(Text, nullable=True)
    min_players = Column(Integer, nullable=False)
    max_players = Column(Integer, nullable=False)
    banner_link = Column(Text, nullable=True)
    # playcount_offset = Column(Integer, default=0)

    logs = relationship("GameLog", back_populates="game", cascade="all, delete-orphan")


class GameLog(Base):
    __tablename__ = "game_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("game_list.id"), nullable=False)
    chosen_at = Column(TIMESTAMP, default=datetime.utcnow)
    ignored = Column(Boolean, default=False)

    game = relationship("Game", back_populates="logs")
