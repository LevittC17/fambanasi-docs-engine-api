"""
Validation utilities for input validation.

Provides functions to validate file paths, markdown syntax,
and other user inputs.
"""

import re
from pathlib import Path

from app.core.exceptions import ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_file_path(path: str, allow_absolute: bool = False) -> None:
    """
    Validate file path for security and format.

    Args:
        path: File path to validate
        allow_absolute: Whether to allow absolute paths

    Raises:
        ValidationError: If path is invalid or unsafe
    """
    if not path:
        raise ValidationError("Path cannot be empty")

    # Check for null bytes
    if "\x00" in path:
        raise ValidationError("Path cannot contain null bytes")

    # Check for absolute paths (unless allowed)
    if not allow_absolute and Path(path).is_absolute():
        raise ValidationError("Absolute paths are not allowed")

    # Check for parent directory references
    if ".." in path:
        raise ValidationError("Path cannot contain parent directory references (..)")

    # Check for leading slash (unless absolute paths allowed)
    if not allow_absolute and path.startswith("/"):
        raise ValidationError("Path should not start with /")

    # Check for invalid characters
    invalid_chars = ["<", ">", ":", '"', "|", "?", "*"]
    for char in invalid_chars:
        if char in path:
            raise ValidationError(f"Path cannot contain character: {char}")

    # Check for consecutive slashes
    if "//" in path:
        raise ValidationError("Path cannot contain consecutive slashes")

    # Validate file extension
    if not path.endswith(".md"):
        raise ValidationError("File must have .md extension")


def validate_markdown_syntax(content: str) -> tuple[bool, list[str]]:
    """
    Validate markdown syntax and common issues.

    Args:
        content: Markdown content to validate

    Returns:
        Tuple of (is_valid, list of warning messages)
    """
    warnings = []

    # Check for unclosed code blocks
    code_block_count = content.count("```")
    if code_block_count % 2 != 0:
        warnings.append("Unclosed code block detected")

    # Check for malformed links
    links = re.findall(r"\[([^\]]*)\]\(([^)]*)\)", content)
    for text, url in links:
        if not url:
            warnings.append(f"Empty URL in link: [{text}]()")

    # Check for malformed images
    images = re.findall(r"!\[([^\]]*)\]\(([^)]*)\)", content)
    for alt, url in images:
        if not url:
            warnings.append(f"Empty URL in image: ![{alt}]()")

    # Check for unbalanced emphasis markers
    if content.count("**") % 2 != 0:
        warnings.append("Unbalanced bold markers (**)")
    if content.count("__") % 2 != 0:
        warnings.append("Unbalanced bold markers (__)")

    # Check for empty headings
    empty_headings = re.findall(r"^#{1,6}\s*$", content, re.MULTILINE)
    if empty_headings:
        warnings.append(f"Found {len(empty_headings)} empty heading(s)")

    is_valid = len(warnings) == 0
    return is_valid, warnings


def validate_slug(slug: str) -> None:
    """
    Validate URL slug format.

    Args:
        slug: Slug to validate

    Raises:
        ValidationError: If slug is invalid
    """
    if not slug:
        raise ValidationError("Slug cannot be empty")

    # Check format (lowercase, hyphens, numbers only)
    if not re.match(r"^[a-z0-9-]+$", slug):
        raise ValidationError("Slug must contain only lowercase letters, numbers, and hyphens")

    # Check for leading/trailing hyphens
    if slug.startswith("-") or slug.endswith("-"):
        raise ValidationError("Slug cannot start or end with hyphen")

    # Check for consecutive hyphens
    if "--" in slug:
        raise ValidationError("Slug cannot contain consecutive hyphens")

    # Check length
    if len(slug) > 200:
        raise ValidationError("Slug cannot exceed 200 characters")
