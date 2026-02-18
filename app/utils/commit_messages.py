"""
Commit message generation utilities.

Automatically generates meaningful commit messages for documentation
changes following conventional commit format.
"""

from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_commit_message(
    action: str,
    path: str,
    title: str | None = None,
    new_path: str | None = None,
) -> str:
    """
    Generate a meaningful commit message for documentation changes.

    Follows conventional commit format: <type>: <description>

    Args:
        action: Type of action (create, update, delete, move)
        path: Path to the document
        title: Document title (if available)
        new_path: New path (for move operations)

    Returns:
        Formatted commit message

    Example:
        >>> generate_commit_message("create", "docs/api/auth.md", "Authentication Guide")
        "docs: Create Authentication Guide"
    """
    # Extract filename from path
    filename = path.split("/")[-1].replace(".md", "")

    # Use title if provided, otherwise use filename
    doc_name = title or filename.replace("-", " ").replace("_", " ").title()

    # Generate message based on action
    if action == "create":
        message = f"docs: Create {doc_name}"
    elif action == "update":
        message = f"docs: Update {doc_name}"
    elif action == "delete":
        message = f"docs: Delete {doc_name}"
    elif action == "move":
        new_filename = new_path.split("/")[-1].replace(".md", "") if new_path else "unknown"
        message = f"docs: Move {doc_name} to {new_filename}"
    else:
        message = f"docs: Modify {doc_name}"

    # Add path context if not obvious
    if "/" in path and path.count("/") > 1:
        category = path.split("/")[1] if path.startswith("docs/") else path.split("/")[0]
        message += f" ({category})"

    return message


def format_bulk_commit_message(changes: list[dict[str, Any]]) -> str:
    """
    Generate commit message for bulk operations.

    Args:
        changes: List of change dictionaries with 'action' and 'path'

    Returns:
        Formatted commit message summarizing all changes

    Example:
        >>> changes = [
        ...     {"action": "create", "path": "docs/a.md"},
        ...     {"action": "update", "path": "docs/b.md"}
        ... ]
        >>> format_bulk_commit_message(changes)
        "docs: Bulk update - 2 documents modified"
    """
    if not changes:
        return "docs: Bulk update"

    action_counts: dict[str, int] = {}
    for change in changes:
        action = change.get("action", "modify")
        action_counts[action] = action_counts.get(action, 0) + 1

    total = len(changes)

    if len(action_counts) == 1:
        action = list(action_counts.keys())[0]
        return f"docs: Bulk {action} - {total} documents"

    parts = []
    for action, count in action_counts.items():
        parts.append(f"{count} {action}d")

    return f"docs: Bulk update - {', '.join(parts)}"
