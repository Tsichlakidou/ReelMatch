from database import SessionLocal
from models import UserShow, Shows
from watchlist_service import update_user_show

db = SessionLocal()

try:
    user_show = (
        db.query(UserShow)
        .join(Shows, UserShow.show_id == Shows.id)
        .filter(
            UserShow.user_id == 2,
            Shows.tmdb_id == 496243,
            Shows.media_type == "movie"
        )
        .first()
    )

    if user_show is None:
        print("Movie not found")
    else:
        print("Before:", user_show.status, user_show.rating)

        result = update_user_show(
            user_id=2,
            user_show_id=user_show.id,
            rating=9,
            db=db
        )

        print("Result:", result)

finally:
    db.close()