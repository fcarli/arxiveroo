import datetime
import urllib.parse

import feedparser

from arxiveroo.tools.query.formatters import format_entries
from arxiveroo.tools.query.models import Entry


def get_pdf_link(entry) -> str:
    """Extract the PDF link from an arXiv entry.
    arXiv entries have a link to the page, we convert it to the PDF URL.

    Args:
        entry: A feedparser entry from arXiv

    Returns:
        str: The PDF link for the paper

    """
    # arXiv page URL format: https://arxiv.org/abs/2403.12345
    # PDF URL format: https://arxiv.org/pdf/2403.12345.pdf
    page_url = entry.link
    if not page_url:
        return ""
    # Replace 'abs' with 'pdf' and append '.pdf'
    return page_url.replace("/abs/", "/pdf/") + ".pdf"


def fetch_arxiv_papers(
    categories: list[str] | str = "cs.AI",
    max_results: int = 200,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
) -> list[Entry]:
    """Fetch papers from arXiv API.

    The function takes as input the categories, max_results, start_date, and end_date.
    It then fetches the papers from the arXiv API and returns them in a list of Entry objects.

    Args:
        categories: Single category or list of categories to filter papers by (e.g., "cs.AI", ["cs.AI", "cs.LG"])
        max_results: Maximum number of results to fetch (defaults to 200, integer)
        start_date: Start date for paper search (defaults to today, datetime.date object)
        end_date: End date for paper search (defaults to today, datetime.date object)

    Returns:
        List of formatted entries, list of Entry objects

    """
    # Convert single category to list for consistent processing
    if isinstance(categories, str):
        categories = [categories]

    # Set default dates if not provided
    today = datetime.datetime.utcnow().date()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = today

    # Construct the arXiv API query URL
    base_url = "http://export.arxiv.org/api/query?"
    # Join categories with OR operator
    search_query = " OR ".join(f"cat:{cat}" for cat in categories)

    # Add date range to the search query if provided
    if start_date or end_date:
        date_query = []
        if start_date:
            date_query.append(f"submittedDate:[{start_date.strftime('%Y%m%d')}000000 TO ")
        else:
            date_query.append("submittedDate:[00000000000000 TO ")

        if end_date:
            date_query.append(f"{end_date.strftime('%Y%m%d')}235959]")
        else:
            date_query.append("99999999999999]")

        date_filter = "".join(date_query)
        search_query = f"({search_query}) AND {date_filter}"

    # Encode the search query to handle special characters like spaces
    encoded_search_query = urllib.parse.quote(search_query)
    query_url = (
        f"{base_url}search_query={encoded_search_query}"
        f"&start=0&max_results={max_results}"
        f"&sortBy=submittedDate&sortOrder=descending"
    )

    # Parse the Atom feed from arXiv
    feed = feedparser.parse(query_url)
    print(f"Total entries fetched: {len(feed.entries)}")

    # Filter and format entries
    entries = []
    for entry in feed.entries:
        # Parse the published date from the entry
        published_str = entry.published  # e.g., "2025-04-05T12:34:56Z"
        published_date = datetime.datetime.strptime(published_str, "%Y-%m-%dT%H:%M:%SZ").date()

        if start_date <= published_date <= end_date:
            # Format the entry to match bioRxiv structure
            formatted_entry = Entry(
                title=entry.title.strip().replace("\n", " "),
                authors=", ".join(author.name for author in entry.authors),
                published=published_date.strftime("%d/%m/%Y"),
                link=get_pdf_link(entry),
                summary=entry.summary,
                category=entry.primary_category.term if hasattr(entry, "primary_category") else categories[0],
                database="arxiv",
            )
            entries.append(formatted_entry)

    return format_entries(entries, start_date, end_date), entries


if __name__ == "__main__":
    # Parameters
    categories = ["cs.AI"]  # List of categories to filter by
    max_results = 200  # Number of results to fetch

    # Example of using custom date range
    start_date = datetime.date(2025, 4, 3)
    end_date = datetime.date(2025, 4, 7)

    # Fetch and process papers
    text, entries = fetch_arxiv_papers(categories, max_results, start_date, end_date)

    # Print results in similar format to bioarxiv.py
    print(f"Papers from {start_date} to {end_date}: {len(entries)}")
    for entry in entries:
        print(f"\nTitle: {entry.title}")
        print(f"Authors: {entry.authors}")
        print(f"Published: {entry.published}")
        print(f"Link: {entry.link}")
        print(f"Category: {entry.category}")
        print(f"Summary: {entry.summary[:200]}...")  # Print first 200 chars of summary
