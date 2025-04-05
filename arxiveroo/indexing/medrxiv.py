"""Module to scrape the categories from the medrxiv collection."""

import pandas as pd
import requests
from bs4 import BeautifulSoup
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, create_model


def scrape_categories() -> list[str]:
    """Scrape the categories from the medrxiv collection.

    Returns:
        list[str]: A list of categories

    """
    # Define the URL to scrape
    url = "https://www.medrxiv.org/collection"

    # Use headers to mimic a browser
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
        )
    }

    # Fetch the page content
    response = requests.get(url, headers=headers, timeout=10)
    html_content = response.content

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # Use a CSS selector to find the <ul> element with id "collection"
    collection_ul = soup.select_one("ul#collection")
    if not collection_ul:
        return []
    # Find all <li> elements within the collection <ul>
    li_elements = collection_ul.find_all("li")

    collections = []
    for li in li_elements:
        # Use CSS selectors to locate the wrapper
        data_wrapper = li.select_one("div.data-wrapper")
        if not data_wrapper:
            continue

        # Get the collection name (check for an <a> tag first)
        a_tag = data_wrapper.find("a")
        name = a_tag.get_text(strip=True) if a_tag else data_wrapper.get_text(strip=True)

        collections.append(name)

    return collections


def create_category_model(categories: list[str]) -> type[BaseModel]:
    """Create a Pydantic model for the categories.

    Args:
        categories: A list of categories

    Returns:
        type[BaseModel]: A Pydantic model for the categories

    """
    fields = dict.fromkeys(categories, (str, ...))
    # Dynamically create the model
    DynamicModel = create_model("DynamicModel", **fields)

    return DynamicModel


def get_medrxiv_categories() -> pd.DataFrame:
    """Get the categories from the medrxiv collection.

    Returns:
        pd.DataFrame: A pandas dataframe containing the categories

    """
    categories = scrape_categories()
    CategoryModel = create_category_model(categories)
    model = init_chat_model("mistralai:mistral-large-latest", temperature=0.0)
    model = model.with_structured_output(CategoryModel)
    response = model.invoke(
        "You are given a list of categories from the medrxiv collection. For each of the following categories, please provide a short description of the category (1-2 sentences maximum)"
    )
    # parse the response into a pandas dataframe
    response_dict = response.model_dump()
    response_df = pd.DataFrame.from_dict(response_dict, orient="index", columns=["description"]).reset_index()
    response_df.columns = ["category_code", "description"]
    response_df["database"] = "medrxiv"
    return response_df


if __name__ == "__main__":
    categories = get_medrxiv_categories()
    print(categories)
