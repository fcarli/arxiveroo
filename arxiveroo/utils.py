"""Utility functions for arxiveroo."""

import json
from pathlib import Path


def load_user_preferences(preference_dir: Path):
    """Load the user preferences and categories from the preference directory.

    Args:
        preference_dir: The path to the preference directory

    Returns:
        user_preferences: The user preferences
        categories: The categories

    """
    try:
        with Path(preference_dir / "user_preferences.json").open("r") as f:
            user_preferences = json.load(f)

        with Path(preference_dir / "categories.json").open("r") as f:
            categories = json.load(f)

        return user_preferences, categories

    except FileNotFoundError:
        raise FileNotFoundError("User preferences file not found. Please run the Initialize tool first.")
