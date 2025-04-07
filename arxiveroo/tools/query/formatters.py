from .models import Entry


def format_entries(entries: list[Entry]) -> str:
    """Format a list of Entry objects into a human-readable string.

    Args:
        entries: List of ArxivEntry objects to format

    Returns:
        str: Formatted string containing paper information

    """
    output = [f"Papers from this week: {len(entries)}"]

    for idx, entry in enumerate(entries):
        paper_info = [
            f"## {entry.title.strip()}",
            f"**Authors:** {entry.authors}",
            f"**Published:** {entry.published}",
            f"**Link:** {entry.link}",
            f"**Category:** {entry.category}",
            f"**Summary:** {entry.summary}",
        ]
        output.extend(paper_info)

    return "\n".join(output)
