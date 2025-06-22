"""Type stubs for trafilatura package."""

from typing import Dict, Any

class Metadata:
    """Metadata extracted from HTML content."""

    title: str | None
    author: str | None
    date: str | None
    description: str | None

def extract(
    html: str,
    *,
    include_comments: bool = True,
    include_tables: bool = True,
    include_links: bool = False,
    include_images: bool = False,
    favor_recall: bool = False,
    no_fallback: bool = False,
    with_metadata: bool = False,
) -> str | None:
    """Extract main text content from HTML."""
    ...

def extract_metadata(html: str) -> Metadata | None:
    """Extract metadata from HTML content."""
    ...

def bare_extraction(html: str) -> Dict[str, Any] | None:
    """Perform bare extraction returning a dictionary with text and metadata."""
    ...
