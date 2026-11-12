
from sqlalchemy.orm import Session
from models import Shows, UserShow, UserPreferences
from database import SessionLocal
from collections import defaultdict
import json


def get_genre_preferences(user_id: int, db: Session):
    movies = (
        db.query(Shows, UserShow)
        .join(UserShow, UserShow.show_id == Shows.id)
        .filter(
            UserShow.user_id == user_id,
            UserShow.status == "watched",
            Shows.media_type == "movie"
        )
        .all()
    )
    total_movies = len(movies)
    if total_movies == 0:
        return {}

    genre_counts = defaultdict(int)
    genre_ratings = defaultdict(list)
    for movie, user_show in movies:

        if not movie.genres:
            continue
        genres = json.loads(movie.genres)

        for genre in genres:
            genre_counts[genre] += 1
            if user_show.rating is not None:
                genre_ratings[genre].append(user_show.rating)
    genre_scores = {}

    for genre, count in genre_counts.items():
        frequency = count / total_movies
        ratings = genre_ratings[genre]
        if ratings:
            average_rating = sum(ratings) / len(ratings) / 10
            # Ratings gain influence as more are available
            rating_weight = 0.7 * min(len(ratings) / 5, 1)
            score = (
                (1 - rating_weight) * frequency
                + rating_weight * average_rating
            )
        else:
            score = frequency
        genre_scores[genre] = round(score, 3)

    return genre_scores



def get_top_rated_movies(user_id: int, db: Session):
    movies = (
        db.query(Shows, UserShow)
        .join(UserShow, UserShow.show_id == Shows.id)
        .filter(
            UserShow.user_id == user_id,
            UserShow.status == "watched",
            UserShow.rating.isnot(None),
            Shows.media_type == "movie"
        )
        .order_by(
            UserShow.rating.desc(),
            UserShow.added_at.desc()
        )
        .limit(5).all()
    )

    top_movies = []
    for movie, user_show in movies:
        top_movies.append({
            "tmdb_id": movie.tmdb_id,
            "title": movie.title,
            "rating": user_show.rating
        })

    return top_movies


def update_user_preferences(user_id: int, db: Session):
    # 1. Calculate preferences
    genre_scores = get_genre_preferences(user_id, db)
    top_rated_movies = get_top_rated_movies(user_id, db)

    # 2. Check if a profile already exists
    preference = (
        db.query(UserPreferences)
        .filter(UserPreferences.user_id == user_id)
        .first()
    )
    # 3. Update an existing profile
    if preference:
        preference.genre_scores = genre_scores
        preference.top_ratings = top_rated_movies
    # 4. Create a new profile
    else:
        preference = UserPreferences(
            user_id=user_id,
            genre_scores=genre_scores,
            top_ratings=top_rated_movies
        )
        db.add(preference)
    # 5. Save changes
    db.flush()

    return preference


def get_user_preferences(user_id: int, db: Session):
    users_profile = (
        db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    )

    recent_movies = (
        db.query(Shows, UserShow)
        .join(UserShow, UserShow.show_id == Shows.id)
        .filter(
            UserShow.status == "watched",
            UserShow.user_id == user_id,
            UserShow.rating >=7,
            Shows.media_type == "movie"
        ).order_by(UserShow.added_at.desc()).limit(3).all()
    )
    recent_favorites = []

    for movie, user_show in recent_movies:
        recent_favorites.append({
            "tmdb_id": movie.tmdb_id,
            "title": movie.title,
            "rating": user_show.rating,
            "added_at": user_show.added_at.isoformat()
        })

    excluded_movies = (
        db.query(Shows.tmdb_id)
        .join(UserShow, UserShow.show_id == Shows.id)
        .filter(
            UserShow.user_id == user_id,
            Shows.media_type == "movie",
            UserShow.status.in_(["watched", "watchlist"])
        ).all()
    )
    excluded_tmdb_ids = [
        tmdb_id for (tmdb_id,) in excluded_movies
    ]
    return {
        "genre_scores": users_profile.genre_scores if users_profile else {},
        "top_ratings": users_profile.top_ratings if users_profile else [],
        "recent_favorites": recent_favorites,
        "excluded_tmdb_ids": excluded_tmdb_ids
    }

if __name__ == "__main__":
    db = SessionLocal()

    try:
        profile = get_user_preferences(2, db)

        print("Genre scores:", profile["genre_scores"])
        print("Top ratings:", profile["top_ratings"])
        print("Recent favorites:", profile["recent_favorites"])
        print("Excluded TMDB IDs:", profile["excluded_tmdb_ids"])

    finally:
        db.close()