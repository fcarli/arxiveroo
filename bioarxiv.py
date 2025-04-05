import datetime
from dataclasses import dataclass

import requests


@dataclass
class BioArxivEntry:
    """Represents a bioRxiv preprint entry with similar structure to arXiv entries."""

    title: str
    authors: str
    published: str
    link: str
    summary: str
    category: str


def get_pdf_link(entry: dict) -> str:
    """Extract the PDF link from a bioRxiv entry.
    bioRxiv entries have a DOI that needs to be converted to a PDF URL.

    Args:
        entry: A dictionary from bioRxiv API response

    Returns:
        str: The PDF link for the paper

    """
    doi = entry.get("doi", "")
    if not doi:
        return ""
    # Convert DOI to PDF URL
    # Example: 10.1101/2024.03.21.586123 -> https://www.biorxiv.org/content/10.1101/2024.03.21.586123v1.full.pdf
    return f"https://www.biorxiv.org/content/{doi}v1.full.pdf"


def fetch_biorxiv_papers(
    category_filter: str = "Genomics",
    server: str = "biorxiv",
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
) -> list[BioArxivEntry]:
    """Fetch papers from bioRxiv API and format them similarly to arXiv entries.

    Args:
        category_filter: Category to filter papers by
        server: Either "biorxiv" or "medrxiv"
        start_date: Start date for paper search (defaults to today)
        end_date: End date for paper search (defaults to today)

    Returns:
        List of BioArxivEntry objects

    """
    # Set default dates if not provided
    today = datetime.datetime.utcnow().date()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = today

    today_str = end_date.strftime("%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")

    # Construct the bioRxiv API URL
    api_url = f"https://api.biorxiv.org/details/{server}/{start_date_str}/{today_str}"
    print(f"Fetching data from: {api_url}")

    # Fetch the JSON data from bioRxiv
    response = requests.get(api_url)
    if response.status_code != 200:
        print("Error fetching data from bioRxiv API.")
        return []

    data = response.json()
    if "collection" not in data:
        print("No preprint collection found in the API response.")
        return []

    # Filter and format entries
    entries = []
    for entry in data["collection"]:
        if entry.get("category", "").lower() == category_filter.lower():
            # Format the entry to match arXiv structure
            formatted_entry = BioArxivEntry(
                title=entry.get("title", ""),
                authors=entry.get("authors", ""),
                published=entry.get("date", ""),
                link=get_pdf_link(entry),
                summary=entry.get("abstract", ""),
                category=entry.get("category", ""),
            )
            entries.append(formatted_entry)

    return entries


if __name__ == "__main__":
    # Parameters
    category_filter = "Genomics"  # Replace with your desired category
    server = "biorxiv"  # Use "biorxiv" or "medrxiv"

    # Example of using custom date range
    start_date = datetime.date(2024, 3, 1)
    end_date = datetime.date(2024, 3, 15)

    # Fetch and process papers
    entries = fetch_biorxiv_papers(category_filter, server, start_date, end_date)

    # Print results in similar format to arxiv.py
    print(f"Total entries fetched: {len(entries)}")
    for entry in entries:
        print(f"\nTitle: {entry.title}")
        print(f"Authors: {entry.authors}")
        print(f"Published: {entry.published}")
        print(f"Link: {entry.link}")
        print(f"Category: {entry.category}")
        print(f"Summary: {entry.summary[:200]}...")  # Print first 200 chars of summary
