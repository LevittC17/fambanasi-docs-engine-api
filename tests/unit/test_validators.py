"""Unit tests for validation utilities."""

import pytest

from app.core.exceptions import ValidationError
from app.utils.validators import (
    validate_file_path,
    validate_markdown_syntax,
    validate_slug,
)


class TestValidateFilePath:
    """Tests for validate_file_path function."""

    def test_valid_path_accepted(self):
        """Test valid markdown path is accepted."""
        validate_file_path("docs/api/authentication.md")  # Should not raise

    def test_empty_path_raises(self):
        """Test empty path raises ValidationError."""
        with pytest.raises(ValidationError, match="empty"):
            validate_file_path("")

    def test_directory_traversal_raises(self):
        """Test path with .. raises ValidationError."""
        with pytest.raises(ValidationError, match="parent directory"):
            validate_file_path("docs/../secrets.md")

    def test_absolute_path_raises(self):
        """Test absolute path raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_file_path("/etc/passwd.md")

    def test_leading_slash_raises(self):
        """Test path with leading slash raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_file_path("/docs/guide.md")

    def test_non_markdown_extension_raises(self):
        """Test non-markdown extension raises ValidationError."""
        with pytest.raises(ValidationError, match=".md"):
            validate_file_path("docs/config.yaml")

    def test_null_bytes_raise(self):
        """Test null bytes in path raise ValidationError."""
        with pytest.raises(ValidationError, match="null"):
            validate_file_path("docs/\x00evil.md")

    def test_consecutive_slashes_raise(self):
        """Test consecutive slashes raise ValidationError."""
        with pytest.raises(ValidationError, match="consecutive"):
            validate_file_path("docs//api/guide.md")


class TestValidateMarkdownSyntax:
    """Tests for validate_markdown_syntax function."""

    def test_valid_markdown_passes(self):
        """Test valid markdown returns no warnings."""
        content = "# Title\n\nThis is a paragraph.\n\n## Section\n\nMore content."
        is_valid, warnings = validate_markdown_syntax(content)
        assert is_valid
        assert len(warnings) == 0

    def test_unclosed_code_block_detected(self):
        """Test unclosed code block is detected."""
        content = "# Title\n\n```python\ncode here\n"
        is_valid, warnings = validate_markdown_syntax(content)
        assert not is_valid
        assert any("code block" in w for w in warnings)

    def test_empty_link_url_detected(self):
        """Test empty link URL is detected."""
        content = "# Title\n\n[Click here]()"
        is_valid, warnings = validate_markdown_syntax(content)
        assert any("Empty URL" in w for w in warnings)

    def test_empty_heading_detected(self):
        """Test empty heading is detected."""
        content = "# \n\nContent here."
        is_valid, warnings = validate_markdown_syntax(content)
        assert any("empty heading" in w.lower() for w in warnings)

    def test_multiple_issues_all_reported(self):
        """Test multiple issues are all reported."""
        content = "```\nunclosed\n\n[bad link]()\n\n#"
        is_valid, warnings = validate_markdown_syntax(content)
        assert not is_valid
        assert len(warnings) >= 2


class TestValidateSlug:
    """Tests for validate_slug function."""

    def test_valid_slug_accepted(self):
        """Test valid slug is accepted."""
        validate_slug("my-document-slug")  # Should not raise

    def test_empty_slug_raises(self):
        """Test empty slug raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("")

    def test_uppercase_raises(self):
        """Test uppercase in slug raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("My-Slug")

    def test_spaces_raise(self):
        """Test spaces in slug raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("my slug")

    def test_leading_hyphen_raises(self):
        """Test leading hyphen raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("-my-slug")

    def test_trailing_hyphen_raises(self):
        """Test trailing hyphen raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("my-slug-")

    def test_consecutive_hyphens_raise(self):
        """Test consecutive hyphens raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_slug("my--slug")

    def test_numbers_allowed(self):
        """Test numbers are allowed in slugs."""
        validate_slug("api-v2-reference")  # Should not raise
