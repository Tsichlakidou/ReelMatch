from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

class UserCreate(BaseModel):
    username: str
    email: str

class UserResponse(BaseModel):
    username: str
    email: str
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None

class ShowCreate(BaseModel):
    tmdb_id: int
    media_type: Literal["movie", "tv"]
    title: str
    overview: str | None = None
    genres: str | None = None
    runtime_minutes: int | None = None

class ShowResponse(BaseModel):
    id: int
    tmdb_id: int
    media_type: Literal["movie", "tv"]
    title: str
    overview: str | None = None
    genres: str | None = None
    runtime_minutes: int | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class WatchlistAdd(BaseModel):
    tmdb_id: int
    media_type: Literal["movie", "tv"]

class WatchlistUpdate(BaseModel):
    status: Literal["watchlist", "watching", "watched"] | None = None
    rating: int | None = Field(default=None, ge=1, le=10)

class WatchlistResponse(BaseModel):
    title: str
    media_type: Literal["movie", "tv"]
    status: Literal["watchlist", "watching", "watched"]
    rating: int | None = None
    show_id: int
    genres: list[str] | None = None

class UserShowResponse(BaseModel):
    id: int
    user_id: int
    show_id: int
    status: Literal["watchlist", "watching", "watched"]
    rating: int | None = None
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WatchlistAddResponse(BaseModel):
    message: str
    user_show_id: int

class AssistantRequest(BaseModel):
    message: str

class AssistantIntent(BaseModel):
    intent: Literal["add_to_watchlist"]
    title: str
    year: int | None = None

class ShowMatch(BaseModel):
    tmdb_id: int
    media_type: Literal["movie", "tv"]
    title: str
    release_date: str | None = None
    popularity: float | None = None

class AssistantResponse(BaseModel):
    status: Literal["success", "not_found", "multiple_matches"]
    message: str | None = None
    user_show_id: int | None = None
    matches: list[ShowMatch] | None = None
    show: ShowMatch | None = None