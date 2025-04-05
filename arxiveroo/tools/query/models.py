from dataclasses import dataclass


@dataclass
class ArxivEntry:
    """Represents an arXiv paper entry."""

    title: str
    authors: str
    published: str
    link: str
    summary: str
    category: str


@dataclass
class BioArxivEntry:
    """Represents a bioRxiv preprint entry with similar structure to arXiv entries."""

    title: str
    authors: str
    published: str
    link: str
    summary: str
    category: str


@dataclass
class MedArxivEntry:
    """Represents a medRxiv preprint entry with similar structure to arXiv entries."""

    title: str
    authors: str
    published: str
    link: str
    summary: str
    category: str
