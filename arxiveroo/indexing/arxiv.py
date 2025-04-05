"""Module to scrape the categories from the arxiv collection."""

import pandas as pd
import requests
from bs4 import BeautifulSoup


def get_arxiv_categories() -> pd.DataFrame:
    """Get the categories from the arxiv collection.

    Returns:
        pd.DataFrame: A pandas dataframe containing the categories

    """
    url = "https://arxiv.org/category_taxonomy"

    # Fetch the HTML content directly from the website
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve page, status code: {response.status_code}")

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")

    # Initialize list to hold (category_code, description) tuples
    categories = []

    # The category entries are in divs with classes "columns divided"
    # Adjust the selector if the HTML structure changes in the future
    for entry in soup.select("div.columns.divided"):
        header_div = entry.find("div", class_="column is-one-fifth")
        columns = entry.find_all("div", class_="column")
        if header_div and len(columns) >= 2:
            # The header contains something like: "cs.AI (Artificial Intelligence)"
            header_text = header_div.get_text(" ", strip=True)
            cat_code = header_text.split("(")[0].strip()  # Extract code before '('
            # The second column contains the description in a <p> tag
            description = columns[1].get_text(" ", strip=True)
            categories.append((cat_code, description))

    categories_df = pd.DataFrame(categories, columns=["category_code", "description"])
    categories_df["database"] = "arxiv"

    return categories_df


if __name__ == "__main__":
    categories = get_arxiv_categories()
    print(categories)
