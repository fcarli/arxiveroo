from dataclasses import dataclass


@dataclass
class Entry:
    """Represents a paper entry."""

    title: str
    authors: str
    published: str
    link: str
    summary: str
    category: str
    database: str

