"""Fetch all papers from all resources."""

import asyncio
import datetime
import importlib.resources
import os
import pathlib
from typing import Annotated

import chainlit as cl
import dotenv
import pandas as pd
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

from arxiveroo.utils import load_user_preferences

from arxiveroo.tools.query.arxiv import fetch_arxiv_papers
from arxiveroo.tools.query.bioarxiv import fetch_biorxiv_papers
from arxiveroo.tools.query.medrxiv import fetch_medrxiv_papers

fetch_arxiv_papers = cl.step(type="tool")(fetch_arxiv_papers)
fetch_biorxiv_papers = cl.step(type="tool")(fetch_biorxiv_papers)
fetch_medrxiv_papers = cl.step(type="tool")(fetch_medrxiv_papers)

dotenv.load_dotenv()

# Define the preference directory path
preference_path_env = os.getenv("PREFERENCE_PATH")
if preference_path_env:
    PREFERENCE_DIR = pathlib.Path(preference_path_env)
else:
    PREFERENCE_DIR = pathlib.Path.home() / ".cache" / "arxiveroo"


# Ensure the directory exists
PREFERENCE_DIR.mkdir(parents=True, exist_ok=True)

# Define the relevance prompt
RELEVANCE_PROMPT = """
You are a helpful assistant with expertise in biomedical research that can annotate papers according to the user's preference.

You annotate the paper by saying whether it is relevant or not providing a reason and by giving a score between 1 and 10 where 1 is the lowest and 10 is the highest. Be granular in your judgement scores.

For example:
- If the user expressed both metododological and apllied interests, papers that match both are more relevant (than papers that match only one of the two).
- Prioritize methodological papers over applied papers or viceversa if the user expressed a preference. Otherwise, papers are equally relevant.

Be selective in your judgement, and don't be afraid to say that a paper is not relevant if it is barely related to the user's preferences.

<user_preferences>
{user_preferences}
</user_preferences>

<paper>
{paper}
</paper>
"""


# Define the entry annotation model
class EntryAnnotation(BaseModel):
    """Represents an annotation for a paper entry and whether it is relevant or not according to the user's preferences."""

    reason: Annotated[str, "The reason for the judgement"]
    is_relevant: Annotated[bool, "Whether the paper is relevant to the user's preferences"]
    relevance_score: Annotated[
        int, "The score of the relevance of the paper to the user's preferences, between 1 and 10, where 1 is the lowest and 10 is the highest"
    ] = Field(ge=1, le=10)


# actual function to call
async def fetch_all_papers(
    start_date: datetime.date | None = None, end_date: datetime.date | None = None, max_results: int = 200
):
    """Fetch all papers from all resources.

    The function takes as input the start_date and end_date. Categories are automatically fetched from pre-saved user preferences.
    It then fetches the papers from all resources, process them for relevance and returns them in a list of Entry objects.

    Args:
        start_date: The start date for the search (defaults to today)
        end_date: The end date for the search (defaults to today)
        max_results: The maximum number of results to fetch (defaults to 200, integer)

    Returns:
        List of Entry objects

    """
    # get the user preferences
    user_preferences, categories = load_user_preferences(PREFERENCE_DIR)

    # read from resources
    with importlib.resources.files("arxiveroo.resources").joinpath("categories_index.csv") as resource_path:
        resources = pd.read_csv(resource_path)

    # get the categories for each source
    categories_by_source = {}
    for source in resources["database"].unique():
        categories_by_source[source] = set(resources[resources["database"] == source]["category_code"])
        categories_by_source[source] = list(categories_by_source[source].intersection(set(categories)))

    _, arxiv_entries = fetch_arxiv_papers(
        categories=categories_by_source["arxiv"],
        start_date=start_date,
        end_date=end_date,
        max_results=max_results,
    )

    _, biorxiv_entries = fetch_biorxiv_papers(
        categories=categories_by_source["biorxiv"],
        start_date=start_date,
        end_date=end_date,
    )
    _, medrxiv_entries = fetch_medrxiv_papers(
        categories=categories_by_source["medrxiv"],
        start_date=start_date,
        end_date=end_date,
    )
    all_entries = arxiv_entries + biorxiv_entries + medrxiv_entries

    idx = 0

    relevant_entries = []

    async with cl.Step(name="Annotating papers") as step:
        for entry in all_entries[:20]:
            model = init_chat_model("google_genai:gemini-2.0-flash", temperature=0.0)
            annotation = await model.with_structured_output(EntryAnnotation).ainvoke(
                RELEVANCE_PROMPT.format(user_preferences=user_preferences, paper=entry)
            )

            step.name = f"Finished annotating paper {idx}"
            if idx == 0:
                step.output = f"Title: {entry.title}\nRelevant: {annotation.is_relevant}\nReason: {annotation.reason}\nScore: {annotation.relevance_score}"
            else:
                step.output += f"\n\nTitle: {entry.title}\nRelevant: {annotation.is_relevant}\nReason: {annotation.reason}\nScore: {annotation.relevance_score}"
            await step.update()
            idx += 1

            # Sleep for a couple of seconds to avoid overwhelming APIs or to allow UI updates
            await asyncio.sleep(2)

            if annotation.is_relevant:
                tdf = pd.DataFrame()
                tdf["title"] = [entry.title]
                tdf["reason"] = [annotation.reason]
                tdf["relevance_score"] = [annotation.relevance_score]
                relevant_entries.append(tdf)

    # Convert the list of DataFrames to a single DataFrame
    relevant_entries = (
        pd.concat(relevant_entries, ignore_index=True)
        .sort_values(by="relevance_score", ascending=False)
        .drop_duplicates(subset="title")
    )

    # Format the DataFrame into a string with each entry as a block
    formatted_output = ""
    idx = 1
    for index, row in relevant_entries.iterrows():
        formatted_output += f"## Paper {idx}\n"
        formatted_output += f"**Title:** {row['title']}\n"
        formatted_output += f"**Score:** {row['relevance_score']}\n"
        formatted_output += f"**Reason:** {row['reason']}\n"
        formatted_output += "\n\n"  # Add an extra line between entries
        idx += 1
    return formatted_output, relevant_entries
