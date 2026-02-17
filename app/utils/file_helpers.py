"""
File processing utilities.

Provides functions for parsing markdown files, extracting frontmatter,
and processing document content.
"""

import re
from typing import Any

import frontmatter

from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Extract YAML frontmatter from markdown content.

    Args:
        content: Markdown content with optional frontmatter

    Returns:
        Tuple of (frontmatter_dict, content_without_frontmatter)

    Example:
        >>> content = "---\\ntitle: Test\\n---\\n# Content"
        >>> meta, body = extract_frontmatter(content)
        >>> meta["title"]
        'Test'
    """
    try:
        post = frontmatter.loads(content)
        return dict(post.metadata), post.content
    except Exception as e:
        logger.warning(f"Failed to parse frontmatter: {e}")
        return {}, content


def parse_markdown(content: str) -> dict[str, Any]:
    """
    Parse markdown content and extract metadata.

    Args:
        content: Markdown content

    Returns:
        Dictionary with parsed information (title, headings, links, etc.)
    """
    metadata, body = extract_frontmatter(content)

    # Extract title (from frontmatter or first H1)
    title = metadata.get("title")
    if not title:
        h1_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        if h1_match:
            title = h1_match.group(1).strip()

    # Extract all headings
    headings = re.findall(r"^(#{1,6})\s+(.+)$", body, re.MULTILINE)

    # Extract links
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", body)

    # Extract images
    images = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", body)

    # Count words (approximate)
    word_count = len(body.split())

    return {
        "title": title,
        "frontmatter": metadata,
        "headings": [{"level": len(level), "text": text} for level, text in headings],
        "links": [{"text": text, "url": url} for text, url in links],
        "images": [{"alt": alt, "url": url} for alt, url in images],
        "word_count": word_count,
        "content": body,
    }


def combine_frontmatter_and_content(frontmatter: dict[str, Any], content: str) -> str:
    """
    Combine frontmatter dictionary and content into markdown string.

    Args:
        frontmatter: Dictionary of frontmatter fields
        content: Markdown content

    Returns:
        Complete markdown document with frontmatter
    """
    if not frontmatter:
        return content

    post = frontmatter.Post(content, **frontmatter)
    return frontmatter.dumps(post)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to be safe for filesystem and Git.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', "-", filename)

    # Replace spaces with hyphens
    filename = filename.replace(" ", "-")

    # Convert to lowercase
    filename = filename.lower()

    # Remove consecutive hyphens
    filename = re.sub(r"-+", "-", filename)

    # Remove leading/trailing hyphens
    filename = filename.strip("-")

    return filename


def generate_slug(text: str) -> str:
    """
    Generate URL-friendly slug from text.

    Args:
        text: Text to convert to slug

    Returns:
        URL-friendly slug

    Example:
        >>> generate_slug("Hello World! This is a Test")
        'hello-world-this-is-a-test'
    """
    # Convert to lowercase
    slug = text.lower()

    # Remove special characters
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)

    # Replace spaces with hyphens
    slug = re.sub(r"\s+", "-", slug)

    # Remove consecutive hyphens
    slug = re.sub(r"-+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    return slug
