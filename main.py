import json

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import User, Shows, UserShow

from schemas import (
    UserCreate,
    UserResponse,
    UserUpdate,
    WatchlistAdd,
    WatchlistUpdate,
    WatchlistResponse,
    UserShowResponse,
    WatchlistAddResponse,
    AssistantRequest,
    AssistantResponse,
)

from ai_assistant import process_message
from tmdb import search_shows
from watchlist_service import add_show_to_watchlist


Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="ReelMatch API",
    description="AI-powered Movie & TV Show Recommendations",
    version="0.1.0"
)


@app.get("/")
def home():
    return {"message": "Welcome to ReelMatch API!"}


@app.post("/users",response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    new_user = User(username=user.username, email=user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get("/users/{user_id}",response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        return user
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.patch("/users/{user_id}",response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = user_update.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user


@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return {"message": "User deleted"}
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.get("/search/shows")
def search_shows_endpoint(query: str):
    shows = search_shows(query)
    return shows


@app.post(
    "/users/{user_id}/watchlist",
    response_model=WatchlistAddResponse,
    status_code=201,
)
def add_to_watchlist(
    user_id: int,
    show_data: WatchlistAdd,
    db: Session = Depends(get_db)
):
    return add_show_to_watchlist(user_id, show_data, db)


@app.get(
    "/users/{user_id}/watchlist",
    response_model=list[WatchlistResponse])
def get_watchlist(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    watchlist = db.query(UserShow, Shows).join(
        Shows, UserShow.show_id == Shows.id
    ).filter(
        UserShow.user_id == user_id
    ).all()

    return [
        {
            "show_id": show.id,
            "title": show.title,
            "media_type": show.media_type,
            "genres": json.loads(show.genres) if show.genres else None,
            "status": user_show.status,
            "rating": user_show.rating,
        }
        for user_show, show in watchlist
    ]


@app.patch(
    "/users/{user_id}/watchlist/{show_id}",
    response_model=UserShowResponse
)
def update_watchlist(
    user_id: int,
    show_id: int,
    update_data: WatchlistUpdate,
    db: Session = Depends(get_db)
):
    user_show = db.query(UserShow).filter(
        UserShow.user_id == user_id, UserShow.show_id == show_id
    ).first()

    if not user_show:
        raise HTTPException(
            status_code=404,
            detail="Show not found in user's watchlist"
        )

    changes = update_data.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(user_show, field, value)

    db.commit()
    db.refresh(user_show)
    return user_show


@app.delete("/users/{user_id}/watchlist/{show_id}")
def delete_from_watchlist(
    user_id: int,
    show_id: int,
    db: Session = Depends(get_db)
):
    user_show = db.query(UserShow).filter(
        UserShow.user_id == user_id,
        UserShow.show_id == show_id
    ).first()

    if not user_show:
        raise HTTPException(
            status_code=404,
            detail="Show not found in user's watchlist"
        )
    db.delete(user_show)
    db.commit()
    return {"message": "Show removed from watchlist"}


@app.post(
    "/users/{user_id}/assistant/chat",
    response_model=AssistantResponse,
    response_model_exclude_none=True
)
def assistant_chat(
    user_id: int,
    request: AssistantRequest,
    db: Session = Depends(get_db)
):
    return process_message(request.message, user_id, db)