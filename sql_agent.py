import json
import time
import sqlite3
from pathlib import Path
from database import SessionLocal
from schemas import WatchlistAdd
from watchlist_service import add_show_to_watchlist
from fastapi import HTTPException
from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import create_agent
from langchain.tools import tool
from tmdb import discover_movies
from langgraph.checkpoint.sqlite import SqliteSaver
from preference_service import get_user_preferences as fetch_user_preferences


db_path = Path(__file__).resolve().parent / "reelmatch.db"

engine = create_engine(
    f"sqlite:///{db_path.as_posix()}"
)

db = SQLDatabase(
    engine,
    include_tables=["shows", "user_shows", "feedback"],
    sample_rows_in_table_info=0,
)

print("Dialect:", db.dialect)
print("Tables:", db.get_usable_table_names())
@tool
def search_tmdb_movies(
    genre_id: int | None = None,
    year: int | None = None,
    release_date_gte: str | None = None,
    release_date_lte: str | None = None,
    vote_average_gte: float | None = None,
    vote_count_gte: int = 100,
    sort_by: str = "vote_average.desc",
    original_language: str | None = None
) -> list[dict]:
    """
    Discover movies using TMDB (The Movie Database), an external
    catalog of movies containing genres, release dates, ratings,
    popularity information, and movie descriptions.

    Use this tool to:
    - Discover movies based on user-specified criteria.
    - Find candidates for personalized recommendations.
    - Explore movies across different genres and time periods.
    - Combine multiple filters for more targeted searches.

    AVAILABLE FILTERS:
    - genre_id: TMDB genre ID. Optional.
    - year: Filter by primary release year.
    - release_date_gte: Earliest release date (YYYY-MM-DD).
    - release_date_lte: Latest release date (YYYY-MM-DD).
    - vote_average_gte: Minimum TMDB rating (0-10).
    - vote_count_gte: Minimum number of user votes.
    - sort_by: Determines the order of search results.
    - original_language: Original language code (e.g. en, fr).

    COMMON GENRE IDS:
    Action=28, Adventure=12, Animation=16, Comedy=35,
    Crime=80, Documentary=99, Drama=18, Family=10751,
    Fantasy=14, History=36, Horror=27, Music=10402,
    Mystery=9648, Romance=10749, Science Fiction=878,
    Thriller=53, War=10752, Western=37.

    SORTING OPTIONS:
    - vote_average.desc: Highest-rated movies first.
    - popularity.desc: Most popular movies first.
    - primary_release_date.desc: Most recent releases first.
    - revenue.desc: Highest-grossing movies first.

    SEARCH GUIDELINES:
    - Choose filters based on the user's actual request.
    - Do not apply unnecessary release date restrictions.
    - For personalized recommendations, consider highly
      rated movies with a meaningful number of votes.
    - Do not assume popularity means personal compatibility.
    - Use vote_average.desc when searching for highly rated
      movies, unless another sorting method is more relevant.
    - Use popularity.desc when the user requests popular or
      trending movies.
    - Use primary_release_date.desc when the user requests
      recent releases.
    - Combine genre, year, and rating filters when useful.
    - All filters are optional and can be combined.

    LIMITATIONS:
    - Returns up to 10 movies per search.
    - Results depend on TMDB's available data.
    - TMDB ratings reflect general audience opinions,
      not the ReelMatch user's personal ratings.
    - This tool does not search actors, directors, or awards.
    """
    return discover_movies(
        genre_id=genre_id,
        year=year,
        release_date_gte=release_date_gte,
        release_date_lte=release_date_lte,
        vote_average_gte=vote_average_gte,
        vote_count_gte=vote_count_gte,
        sort_by=sort_by,
        original_language=original_language
    )

@tool
def add_to_watchlist(user_id: int, tmdb_id: int) -> str:
    """
    Add a movie to the user's watchlist.

    Use this tool only when the user explicitly asks
    to add a movie or confirms a previous suggestion.

    The movie must be identified by its TMDB ID.
    """
    db = SessionLocal()
    try:
        show_data = WatchlistAdd(
            tmdb_id=tmdb_id,
            media_type="movie"
        )
        result = add_show_to_watchlist(
            user_id=user_id,
            show_data=show_data,
            db=db
        )
        return json.dumps(result)
    except HTTPException as e:
        db.rollback()
        return json.dumps({
            "status": "error",
            "status_code": e.status_code,
            "message": e.detail
        })
    finally:
        db.close()


@tool
def get_user_preferences(user_id: int) -> dict:
    """
    Retrieve the user's complete recommendation context:
    genre scores, top-rated movies, recent favorites,
    and TMDB IDs to exclude.

    Use this tool for personalized movie recommendations.
    SQL queries are unnecessary for data already returned here.
    """
    db = SessionLocal()

    try:
        return fetch_user_preferences(user_id, db)
    finally:
        db.close()


load_dotenv(override=True)

llm = ChatOpenAI(
    model="gpt-5-mini",
    reasoning_effort="low"
)

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools() + [
    search_tmdb_movies,
    add_to_watchlist,
    get_user_preferences
    ]

for tool in tools:
    print(tool.name)



system_prompt = """
You are ReelMatch, an autonomous AI movie and TV assistant.

Your purpose is to help users discover, explore,
recommend, and manage movies and TV shows.

You have access to:
- SQLite tools for retrieving and managing user data.
- TMDB discovery tools for finding movie candidates.

Choose tools based on the user's request.
You may combine tools to complete complex tasks.

PERSONALIZED RECOMMENDATIONS:

When a user requests personalized movie recommendations:

1. Call get_user_preferences to retrieve:
   - genre_scores
   - top_ratings
   - recent_favorites
   - excluded_tmdb_ids

2. Analyze the user's preferences:
   - Give more weight to highly rated movies.
   - Consider genres, themes, humor, and storytelling style.
   - Treat genre scores as signals, not definitive preferences.
   - Consider low-rated movies as negative signals when available.

3. Combine overall preferences with recent favorites.
   Use both to understand the user's current interests.

4. Use search_tmdb_movies to discover suitable candidates.
   Choose filters based on the user's preferences.
   Do not automatically prioritize popularity, release date,
   or TMDB ratings.

5. Compare candidates using genres, overviews, themes,
   and similarities to highly rated movies.

6. Exclude candidates whose TMDB IDs appear in
   excluded_tmdb_ids.

7. Recommend ONE movie unless the user requests more.
   Explain why the recommendation matches their preferences.

8. Do not use SQL tools to retrieve information already
   provided by get_user_preferences.

9. Use SQL tools only when additional information is
   genuinely necessary.

If preference data is insufficient, do not invent preferences.

TOOL USAGE AND EFFICIENCY:

- Prefer get_user_preferences for retrieving saved
  preference profiles.

- Do not use SQL tools to recalculate genre scores
  or top-rated movies already available in the profile.

- Use SQL tools for additional information that the
  preference profile does not contain.

- Minimize unnecessary tool calls.
- Inspect the database schema before writing SQL,
  unless the required schema is already available.
- Combine related database retrievals when possible.
- Avoid repeating queries that retrieve the same data.

- Use at most 2 TMDB discovery searches per recommendation.
- Never repeat a search with the same genre and similar filters.
- Only perform a second search if the first search produces
  no suitable candidates after applying exclusions.
- Evaluate the candidates already retrieved before
  deciding whether another search is necessary.
- The user's specific request (e.g. dark comedy) takes
  priority over their highest-scoring general genre.

- Prioritize relevant candidates over large result sets.

DATABASE RULES:

Available tables:
- shows: Movie and TV metadata.
- user_shows: User watchlist, watched status, and ratings.

Important:
- shows.id is the internal database ID.
- shows.tmdb_id is the external TMDB ID.
- user_shows.show_id references shows.id.
- user_shows.added_at is not necessarily the watch date.

Never assume unknown column names.
Inspect the schema when needed.

- Use the requested user_id for user-specific queries.
- Check SQL queries before executing them.
- Do not modify database schemas.
- Only modify user data when explicitly requested.
- Never claim an operation succeeded unless
  the database result confirms success.
The user_shows table has a "status" column,
not a "watched" column.

To identify watched movies, use:
user_shows.status = 'watched'

Never reference user_shows.watched.


DATABASE UPDATE OPERATIONS:

When the user requests to update an existing movie
or TV show (watched status, rating, feedback):

1. Identify the target show using conversation context.
   Do not search for it again if its identity is clear.

2. Identify the correct user_show record.
   Always verify that it belongs to the current user.

3. Prefer an existing custom tool when available.

4. If no custom tool exists, minimize SQL operations.
   Combine related updates when appropriate.

5. Never update a record without checking its ownership.

6. After executing an update, verify that the
   intended change was saved successfully.

7. Never modify records belonging to other users.


WATCHLIST OPERATIONS:

- After recommending a movie, ask the user whether
  they want to add it to their watchlist.
- Never add a recommendation automatically.
- If the user confirms, use the add_to_watchlist tool.
- Use the TMDB ID of the selected movie.
- Do not confuse TMDB IDs with internal database IDs.
- Confirm success only after the tool returns success.
- If the movie already exists in the watchlist,
  inform the user without creating duplicates.
  
Respond in the same language as the user.
"""
system_prompt += (
    "\nDATABASE SCHEMA:\n"
    + db.get_table_info()
    + "\nUse this schema for SQL queries. "
      "Do not call sql_db_list_tables or sql_db_schema "
      "unless you encounter a schema-related error."
)

memory_path = Path(__file__).resolve().parent / "reelmatch_memory.db"

memory_connection = sqlite3.connect(
    memory_path,
    check_same_thread=False
)

memory = SqliteSaver(memory_connection)

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
    checkpointer=memory
)
config = {
    "configurable": {
        "thread_id": "test_dark_comedy_2"
    }
}


if __name__ == "__main__":
    while True:
        user_message = input("\nYou: ").strip()

        if user_message.lower() in ["exit", "quit"]:
            break

        if not user_message:
            continue

        previous_messages = agent.get_state(config).values.get("messages", [])
        previous_count = len(previous_messages)

        start = time.perf_counter()

        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config
        )

        elapsed = time.perf_counter() - start

        new_messages = result["messages"][previous_count:]

        input_tokens = 0
        output_tokens = 0
        tool_calls = []

        for message in new_messages:
            usage = getattr(message, "usage_metadata", None)

            if usage:
                input_tokens += usage.get("input_tokens", 0)
                output_tokens += usage.get("output_tokens", 0)

            tool_calls.extend(getattr(message, "tool_calls", None) or [])

        print("\nReelMatch:", result["messages"][-1].content)

        print("\n--- METRICS ---")
        print("Input tokens:", input_tokens)
        print("Output tokens:", output_tokens)
        print("Total tokens:", input_tokens + output_tokens)
        print("Tool calls:", len(tool_calls))
        print("Tools used:", [call["name"] for call in tool_calls])
        print(f"Execution time: {elapsed:.2f}s")