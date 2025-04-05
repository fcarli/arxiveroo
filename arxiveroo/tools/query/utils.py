from .arxiv import ArxivEntry
from .bioarxiv import BioArxivEntry
from .medrxiv import MedArxivEntry


def format_entries(entries: list[ArxivEntry | BioArxivEntry | MedArxivEntry]) -> str:
    """Format a list of ArxivEntry objects into a human-readable string.

    Args:
        entries: List of ArxivEntry objects to format

    Returns:
        str: Formatted string containing paper information

    """
    output = [f"Papers from this week: {len(entries)}"]

    for idx, entry in enumerate(entries):
        paper_info = [
            #f"\n**Paper {idx + 1}:**",
            f"## {entry.title.strip()}",
            f"**Authors:** {entry.authors}",
            f"**Published:** {entry.published}",
            f"**Link:** {entry.link}",
            f"**Category:** {entry.category}",
            f"**Summary:** {entry.summary}",
        ]
        output.extend(paper_info)

    return "\n".join(output)