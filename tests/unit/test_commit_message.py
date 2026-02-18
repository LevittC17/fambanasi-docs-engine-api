"""Unit tests for commit message generation."""


from app.utils.commit_messages import (
    format_bulk_commit_message,
    generate_commit_message,
)


class TestGenerateCommitMessage:
    """Tests for generate_commit_message function."""

    def test_create_action_with_title(self):
        """Test create action generates correct message with title."""
        msg = generate_commit_message(
            "create", "docs/api/auth.md", "Authentication Guide"
        )
        assert msg.startswith("docs:")
        assert "Create" in msg
        assert "Authentication Guide" in msg

    def test_update_action(self):
        """Test update action generates correct message."""
        msg = generate_commit_message(
            "update", "docs/api/auth.md", "Authentication Guide"
        )
        assert "Update" in msg
        assert "Authentication Guide" in msg

    def test_delete_action(self):
        """Test delete action generates correct message."""
        msg = generate_commit_message(
            "delete", "docs/api/auth.md", "Authentication Guide"
        )
        assert "Delete" in msg

    def test_move_action_with_new_path(self):
        """Test move action includes destination."""
        msg = generate_commit_message(
            "move", "docs/old/file.md", "Old Doc", new_path="docs/new/file.md"
        )
        assert "Move" in msg or "move" in msg.lower()

    def test_action_without_title_uses_filename(self):
        """Test that filename is used when no title provided."""
        msg = generate_commit_message("create", "docs/api/rate-limiting.md")
        assert "Rate Limiting" in msg or "rate-limiting" in msg.lower()

    def test_message_starts_with_docs_prefix(self):
        """Test all messages start with docs: prefix."""
        for action in ["create", "update", "delete"]:
            msg = generate_commit_message(action, "docs/guide.md", "Guide")
            assert msg.startswith("docs:")

    def test_unknown_action_uses_modify(self):
        """Test unknown action defaults to modify."""
        msg = generate_commit_message("archive", "docs/old.md", "Old Doc")
        assert "docs:" in msg


class TestFormatBulkCommitMessage:
    """Tests for format_bulk_commit_message function."""

    def test_empty_changes(self):
        """Test empty changes returns default message."""
        msg = format_bulk_commit_message([])
        assert "docs:" in msg

    def test_single_action_type(self):
        """Test single action type message."""
        changes = [
            {"action": "create", "path": "docs/a.md"},
            {"action": "create", "path": "docs/b.md"},
        ]
        msg = format_bulk_commit_message(changes)
        assert "2" in msg
        assert "docs:" in msg

    def test_multiple_action_types(self):
        """Test multiple action types message."""
        changes = [
            {"action": "create", "path": "docs/a.md"},
            {"action": "update", "path": "docs/b.md"},
            {"action": "delete", "path": "docs/c.md"},
        ]
        msg = format_bulk_commit_message(changes)
        assert "docs:" in msg
