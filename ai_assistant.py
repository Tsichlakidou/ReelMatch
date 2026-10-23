import os
from dotenv import load_dotenv
from openai import OpenAI
from schemas import AssistantIntent, WatchlistAdd, ShowMatch
from tmdb import search_shows
from sqlalchemy.orm import Session
from watchlist_service import add_show_to_watchlist
from conversation_service import save_pending_matches, get_conversation_state

load_dotenv(override=True)

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)
print("OpenAI API key loaded:", bool(api_key))

def detect_intent(message: str):
    instructions = """
    You are an AI assistant for ReelMatch, a movie and TV show application.

    Your task is to identify the user's intent and extract the movie or TV show title.

    Supported intent:
    - add_to_watchlist

    Return the intent and title.
    Do not invent movie titles.
    
    Extract the release year if the user mentions it.
    If no year is mentioned, return null.
    Do not guess or invent a release year.
    """
    response = client.responses.parse(
        model="gpt-4.1-mini",
        instructions=instructions,
        input=message,
        text_format=AssistantIntent
    )
    return response.output_parsed


def find_show(title: str, year: int | None = None):
    shows = search_shows(title)
    matches = []
    if year is not None:
        for show in shows:
            if (
                    show["release_date"]
                    and int(show["release_date"][:4]) == year
                    and show["title"].casefold() == title.casefold()
            ):
                matches.append(show)
    else:
        for show in shows:
            if show["title"].casefold() == title.casefold():
                matches.append(show)

    return matches

def process_message(message: str, user_id: int, db: Session):
    state = get_conversation_state(user_id, db)

    if (
        state is not None
        and state.pending_action == "add_to_watchlist"
        and state.pending_matches
    ):
        pass

    intent_data = detect_intent(message)

    if intent_data.intent == "add_to_watchlist":
        matches = find_show(intent_data.title, intent_data.year)
        if len(matches) == 0:
            return {"status": "not_found", "message": "No matches found."}
        elif len(matches) == 1:
            show = matches[0]
            show_data = WatchlistAdd(
                tmdb_id=show["tmdb_id"],
                media_type=show["media_type"]
            )
            result = add_show_to_watchlist(user_id, show_data, db)
            return {
                "status": "success",
                "message": result["message"],
                "show": show,
                "user_show_id": result["user_show_id"]
            }
        else:
            validated_matches = [ShowMatch(**show) for show in matches]
            matches_data = [match.model_dump() for match in validated_matches]
            save_pending_matches(user_id, matches_data, db)

            return {
                "status": "multiple_matches",
                "matches": validated_matches
            }
if __name__ == "__main__":
    pass