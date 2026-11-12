import os
from dotenv import load_dotenv
import requests
from requests.exceptions import HTTPError, Timeout, ConnectionError
from fastapi import HTTPException

load_dotenv()

TMDB_ACCESS_TOKEN = os.getenv("TMDB_ACCESS_TOKEN")

url = "https://api.themoviedb.org/3/search/multi"

headers = {
    "Authorization": f"Bearer {TMDB_ACCESS_TOKEN}",
    "accept": "application/json"
}


def search_shows(query: str):
    params = {"query": query}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    data = response.json()
    results = []
    for item in data["results"]:
        if item["media_type"] == "movie":
            title = item["title"]
        elif item["media_type"] == "tv":
            title = item["name"]
        else:
            continue

        show = {
            "tmdb_id": item["id"],
            "media_type": item["media_type"],
            "title": title,
            "overview": item.get("overview"),
            "genres": item.get("genre_ids", []),
            "popularity": item.get("popularity"),
            "release_date": item.get("release_date") if item["media_type"] == "movie" else item.get("first_air_date"),
            "poster_path": item.get("poster_path")
        }

        results.append(show)

    return results

def get_show_details(tmdb_id: int, media_type: str):
    url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

    except Timeout:
        raise HTTPException(
            status_code=504,
            detail="TMDB request timed out"
        )

    except ConnectionError:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to TMDB"
        )

    except HTTPError as error:
        if error.response is not None and error.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Show not found in TMDB"
            ) from error

        raise HTTPException(
            status_code=502,
            detail="TMDB API error"
        ) from error

    return data


def discover_movies(
    genre_id: int | None = None,
    year: int | None = None,
    release_date_gte: str | None = None,
    release_date_lte: str | None = None,
    vote_average_gte: float | None = None,
    vote_count_gte: int = 100,
    sort_by: str = "vote_average.desc",
    original_language: str | None = None
):
    discover_url = "https://api.themoviedb.org/3/discover/movie"
    params = {
        "sort_by": sort_by,
        "vote_count.gte": vote_count_gte
    }
    if genre_id is not None:
        params["with_genres"] = genre_id
    if year is not None:
        params["primary_release_year"] = year
    if release_date_gte is not None:
        params["release_date.gte"] = release_date_gte
    if vote_average_gte is not None:
        params["vote_average.gte"] = vote_average_gte
    if original_language is not None:
        params["with_original_language"] = original_language


    response = requests.get(
        discover_url,
        headers=headers,
        params=params,
        timeout=10
    )
    response.raise_for_status()
    data = response.json()
    movies = data.get("results", [])
    results = []
    for movie in movies[:10]:
        show = {
            "tmdb_id": movie["id"],
            "title": movie["title"],
            "overview": movie.get("overview"),
            "genre_ids": movie.get("genre_ids", []),
            "release_date": movie.get("release_date"),
            "vote_average": movie.get("vote_average")
        }
        results.append(show)

    return results


if __name__ == "__main__":
    movies = discover_movies(878)

    for movie in movies[:5]:
        print(movie["title"], movie["vote_average"])