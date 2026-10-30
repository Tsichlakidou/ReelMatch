
from pathlib import Path

from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import create_agent
from langchain.tools import tool
from tmdb import discover_movies

db_path = Path(__file__).resolve().parent / "reelmatch.db"

engine = create_engine(
    f"sqlite:///file:{db_path.as_posix()}?mode=ro&uri=true"
)

db = SQLDatabase(
    engine,
    include_tables=["shows", "user_shows", "user_preferences"],
    sample_rows_in_table_info=0,
)

print("Dialect:", db.dialect)
print("Tables:", db.get_usable_table_names())

@tool
def search_tmdb_movies(genre_id: int) -> list[dict]:
    """Search TMDB for movies belonging to a specific genre.

    Common genre IDs:
    Action = 28
    Comedy = 35
    Drama = 18
    Science Fiction = 878
    Thriller = 53
    """
    return discover_movies(genre_id)


load_dotenv(override=True)

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0
)

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools() + [search_tmdb_movies]

for tool in tools:
    print(tool.name)




system_prompt = """
You are ReelMatch, a personalized movie recommendation agent.

You have access to:
- SQL tools to retrieve user ratings, watched movies,
  genres, and movie descriptions from the SQLite database.
- A TMDB tool to discover new movie candidates.

When recommending a movie:
1. Inspect the database schema before writing SQL.
2. Retrieve the user's watched movies and ratings.
3. Identify which genres and movie characteristics they prefer.
4. Search TMDB for suitable candidates.
5. Compare the candidates with the user's preferences.
6. Recommend ONE movie the user has not already watched.
7. Explain why it matches their taste.

Prioritize personal compatibility over TMDB ratings
or the order of the search results.

SQL rules:
- Only execute read-only queries.
- Check SQL queries before executing them.
- Retrieve only the data needed.
- Use the requested user_id in queries.

Respond in the same language as the user.
"""

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt
)

result = agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": "Recommend a movie for user 2 based on their watched movies and ratings."        }
    ]
})

for message in result["messages"]:
    print("TYPE:", type(message).__name__)
    print("CONTENT:", message.content)
    print("TOOL CALLS:", getattr(message, "tool_calls", None))
    print("----------------------")
