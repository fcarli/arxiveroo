"""Module to generate a comprehensive index of categories from different preprint databases."""

from pathlib import Path

import pandas as pd

from .arxiv import get_arxiv_categories
from .bioarxiv import get_biorxiv_categories
from .medrxiv import get_medrxiv_categories


def generate_index(output_folder: str = "../resources/") -> pd.DataFrame:
    """Generate a comprehensive index of categories from different preprint databases.

    Args:
        output_folder: Path to the folder where the index will be saved

    Returns:
        DataFrame containing the combined categories from all sources

    """
    # Fetch categories from different sources
    arxiv_categories = get_arxiv_categories()
    medrxiv_categories = get_medrxiv_categories()
    biorxiv_categories = get_biorxiv_categories()

    # Combine all categories into a single DataFrame
    all_categories = pd.concat([arxiv_categories, medrxiv_categories, biorxiv_categories])

    # Create output folder if it doesn't exist
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    # Save the combined index to a CSV file
    output_path = Path(output_folder) / "categories_index.csv"
    all_categories.to_csv(output_path, index=False)

    return all_categories
