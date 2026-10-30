from langchain.tools import tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from database import SessionLocal
from models import Shows, UserShow, UserPreferences
import json
from tmdb import discover_movies

load_dotenv()


@tool
def get_user_preferences(user_id: int) -> str:
    """Get a user's saved movie genre preferences and top rated movies."""

    db = SessionLocal()

    try:
        preference = (
            db.query(UserPreferences)
            .filter(UserPreferences.user_id == user_id)
            .first()
        )

        if preference is None:
            return json.dumps({
                "message": "No preference profile found."
            })

        return json.dumps({
            "genre_scores": preference.genre_scores,
            "top_ratings": preference.top_ratings
        })

    finally:
        db.close()


@tool
def search_tmdb_movies(genre_id: int) -> list[dict]:
    """Search TMDB for movies belonging to a specific genre."""

    return discover_movies(genre_id)


llm = ChatOpenAI(model="gpt-4.1-mini")

agent = create_agent(
    model=llm,
    tools=[get_user_preferences, search_tmdb_movies],

    system_prompt="""
    You are ReelMatch, a personalized movie recommendation agent.

    When a user requests a movie recommendation:

    1. Use get_user_preferences to retrieve their saved preferences.

    2. Analyze their genre scores and top-rated movies.
       Consider both genre preferences and the themes,
       storytelling style, and atmosphere of their favorite movies.

    3. Use search_tmdb_movies to retrieve movie candidates.

    4. Evaluate ALL returned candidates before selecting one.
       Compare their overviews, genres, and thematic similarities
       to the user's preferences.

    5. Prioritize personal compatibility over TMDB ratings.
       A movie with a lower TMDB rating may be a better recommendation.

    6. Do not automatically select the first movie in the results.

    7. Recommend ONE movie from the returned TMDB candidates.
       Explain specifically why it matches the user's taste.

    8. Do not recommend movies appearing in the user's top-rated list.

    If all user ratings are low, do not assume those movies
    are favorites. Treat this as insufficient positive
    preference evidence.

    Respond in the same language as the user.
    """
)

result = agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": "Recommend a movie for user 2 based on their preferences."
        }
    ]
})

for message in result["messages"]:
    print("TYPE:", type(message).__name__)
    print("CONTENT:", message.content)
    print("TOOL CALLS:", getattr(message, "tool_calls", None))
    print("----------------------")