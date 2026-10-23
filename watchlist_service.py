from sqlalchemy.orm import Session
from models import User, Shows, UserShow
from schemas import WatchlistAdd
from tmdb import get_show_details
from fastapi import HTTPException
import json

def add_show_to_watchlist(
    user_id: int,
    show_data: WatchlistAdd,
    db: Session
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    show = db.query(Shows).filter(
        Shows.tmdb_id == show_data.tmdb_id,
        Shows.media_type == show_data.media_type
    ).first()
    if not show:
        details = get_show_details(
            show_data.tmdb_id,
            show_data.media_type
        )
        genres = [genre["name"] for genre in details.get("genres", [])]

        title = (
            details["title"]
            if show_data.media_type == "movie"
            else details["name"]
        )

        show = Shows(
            tmdb_id=show_data.tmdb_id,
            media_type=show_data.media_type,
            title=title,
            overview=details.get("overview"),
            runtime_minutes=details.get("runtime") if show_data.media_type == "movie" else None,
            genres=json.dumps(genres)
        )
        db.add(show)
        db.flush()

    existing = db.query(UserShow).filter(
        UserShow.user_id == user_id,
        UserShow.show_id == show.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Show already in watchlist"
        )
    new_user_show = UserShow(
        user_id=user.id,
        show_id=show.id,
        status="watchlist"
    )

    db.add(new_user_show)
    db.commit()
    db.refresh(new_user_show)

    return {
        "message": "Show added to watchlist",
        "user_show_id": new_user_show.id,
    }