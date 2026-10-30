
from sqlalchemy import (Column, Integer, String, DateTime,
                        Text, UniqueConstraint, ForeignKey, JSON)
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

class Shows(Base):
    __tablename__ = "shows"
    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(String(10), nullable=False)
    title = Column(String(255), nullable=False)
    overview = Column(Text, nullable=True)
    genres = Column(Text, nullable=True)
    runtime_minutes = Column(Integer, nullable=True)
    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )
    __table_args__ = (
        UniqueConstraint("tmdb_id", "media_type", name="uq_tmdb_media_type"),
    )

class UserShow(Base):
    __tablename__ = "user_shows"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    show_id = Column(Integer, ForeignKey("shows.id"), nullable=False)
    status = Column(String(20), nullable=False, default="watchlist")
    rating = Column(Integer, nullable=True)
    added_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    __table_args__ = (
        UniqueConstraint("user_id", "show_id", name="uq_user_id_show_id"),
    )

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    user_show_id = Column(Integer, ForeignKey("user_shows.id"), nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        server_default=func.now(),
    )

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    genre_scores = Column(JSON, nullable=False, default=dict)
    top_ratings = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ConversationState(Base):
    __tablename__ = "conversation_states"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )
    pending_action = Column(String(50), nullable=True)
    pending_matches = Column(JSON, nullable=True)