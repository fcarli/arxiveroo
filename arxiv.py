import datetime
import feedparser
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ArxivEntry:
    """Represents an arXiv paper entry with similar structure to bioRxiv entries."""
    title: str
    authors: str
    published: str
    link: str
    summary: str
    category: str

def get_pdf_link(entry) -> str:
    """
    Extract the PDF link from an arXiv entry.
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
    return page_url.replace('/abs/', '/pdf/') + '.pdf'

def fetch_arxiv_papers(
    category: str = "cs.AI", 
    max_results: int = 200,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None
) -> List[ArxivEntry]:
    """
    Fetch papers from arXiv API and format them similarly to bioRxiv entries.
    
    Args:
        category: arXiv category to filter papers by (e.g., "cs.AI")
        max_results: Maximum number of results to fetch
        start_date: Start date for paper search (defaults to today)
        end_date: End date for paper search (defaults to today)
    
    Returns:
        List of ArxivEntry objects
    """
    # Set default dates if not provided
    today = datetime.datetime.utcnow().date()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = today

    # Construct the arXiv API query URL
    base_url = "http://export.arxiv.org/api/query?"
    search_query = f"cat:{category}"
    query_url = (
        f"{base_url}search_query={search_query}"
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
            formatted_entry = ArxivEntry(
                title=entry.title,
                authors=", ".join(author.name for author in entry.authors),
                published=published_str,
                link=get_pdf_link(entry),
                summary=entry.summary,
                category=category
            )
            entries.append(formatted_entry)

    return entries

if __name__ == "__main__":
    # Parameters
    category = "cs.AI"  # Replace with desired category
    max_results = 200  # Number of results to fetch
    
    # Example of using custom date range
    start_date = datetime.date(2024, 3, 1)
    end_date = datetime.date(2024, 3, 15)

    # Fetch and process papers
    entries = fetch_arxiv_papers(category, max_results, start_date, end_date)
    
    # Print results in similar format to bioarxiv.py
    print(f"Papers from this week: {len(entries)}")
    for entry in entries:
        print(f"\nTitle: {entry.title}")
        print(f"Authors: {entry.authors}")
        print(f"Published: {entry.published}")
        print(f"Link: {entry.link}")
        print(f"Category: {entry.category}")
        print(f"Summary: {entry.summary[:200]}...")  # Print first 200 chars of summary