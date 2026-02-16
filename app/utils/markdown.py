"""
Markdown processing utilities.

Provides functions for markdown manipulation, rendering,
and content analysis.
"""

import re

from markdown import markdown as md_to_html

from app.core.logging import get_logger

logger = get_logger(__name__)


def strip_markdown(text: str) -> str:
    """
    Strip markdown formatting from text.

    Args:
        text: Markdown text

    Returns:
        Plain text without markdown formatting
    """
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)

    # Remove headers
    text = re.sub(r"#{1,6}\s+", "", text)

    # Remove emphasis
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)

    # Remove links but keep text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Remove images
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)

    # Remove list markers
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

    # Remove blockquotes
    text = re.sub(r"^\s*>\s+", "", text, flags=re.MULTILINE)

    # Clean up whitespace
    text = re.sub(r"\n\n+", "\n\n", text)

    return text.strip()


def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """
    Estimate reading time in minutes.

    Args:
        text: Text content
        words_per_minute: Average reading speed (default 200 WPM)

    Returns:
        Estimated reading time in minutes (minimum 1)
    """
    # Strip markdown formatting
    plain_text = strip_markdown(text)

    # Count words
    word_count = len(plain_text.split())

    # Calculate reading time
    minutes = max(1, round(word_count / words_per_minute))

    return minutes


def extract_excerpt(text: str, max_length: int = 200) -> str:
    """
    Extract excerpt from text for previews.

    Args:
        text: Full text content
        max_length: Maximum length of excerpt

    Returns:
        Text excerpt
    """
    # Strip markdown
    plain_text = strip_markdown(text)

    # Take first paragraph or max_length characters
    paragraphs = plain_text.split("\n\n")
    excerpt = paragraphs[0] if paragraphs else plain_text

    # Truncate if necessary
    if len(excerpt) > max_length:
        excerpt = excerpt[:max_length].rsplit(" ", 1)[0] + "..."

    return excerpt


def render_markdown_to_html(text: str) -> str:
    """
    Render markdown to HTML.

    Args:
        text: Markdown text

    Returns:
        Rendered HTML
    """
    return md_to_html(
        text,
        extensions=[
            "extra",
            "codehilite",
            "toc",
            "tables",
            "fenced_code",
        ],
    )


def extract_table_of_contents(text: str) -> list[dict[str, str]]:
    """
    Extract table of contents from markdown headings.

    Args:
        text: Markdown text

    Returns:
        List of heading dictionaries with level, text, and anchor
    """
    headings = re.findall(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE)

    toc = []
    for level_str, heading_text in headings:
        level = len(level_str)
        # Generate anchor ID (GitHub style)
        anchor = heading_text.lower()
        anchor = re.sub(r"[^\w\s-]", "", anchor)
        anchor = re.sub(r"[\s_]+", "-", anchor)

        toc.append({
            "level": level,
            "text": heading_text.strip(),
            "anchor": anchor,
        })

    return toc
