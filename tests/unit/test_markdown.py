"""Unit tests for markdown utilities."""

from app.utils.markdown import (
    estimate_reading_time,
    extract_excerpt,
    extract_table_of_contents,
    strip_markdown,
)


class TestStripMarkdown:
    """Tests for strip_markdown function."""

    def test_strips_headings(self):
        """Test heading markers are removed."""
        result = strip_markdown("# Heading One\n## Heading Two")
        assert "#" not in result
        assert "Heading One" in result

    def test_strips_bold(self):
        """Test bold markers are removed but text preserved."""
        result = strip_markdown("**bold text** here")
        assert "**" not in result
        assert "bold text" in result

    def test_strips_italic(self):
        """Test italic markers are removed but text preserved."""
        result = strip_markdown("*italic text* here")
        assert result.count("*") == 0
        assert "italic text" in result

    def test_strips_links(self):
        """Test link syntax is removed but text preserved."""
        result = strip_markdown("[link text](https://example.com)")
        assert "[" not in result
        assert "link text" in result

    def test_strips_code_blocks(self):
        """Test code blocks are removed."""
        result = strip_markdown("```python\ncode here\n```")
        assert "```" not in result

    def test_strips_list_markers(self):
        """Test list markers are removed."""
        result = strip_markdown("- item one\n- item two")
        assert "- item" not in result
        assert "item one" in result


class TestEstimateReadingTime:
    """Tests for estimate_reading_time function."""

    def test_short_content_returns_one_minute(self):
        """Test very short content returns at least 1 minute."""
        result = estimate_reading_time("Hello world.")
        assert result == 1

    def test_longer_content_returns_more_minutes(self):
        """Test longer content returns proportional reading time."""
        # 200 words = ~1 min at 200 WPM
        words = " ".join(["word"] * 600)
        result = estimate_reading_time(words)
        assert result >= 3

    def test_custom_words_per_minute(self):
        """Test custom reading speed changes estimate."""
        words = " ".join(["word"] * 400)
        fast = estimate_reading_time(words, words_per_minute=400)
        slow = estimate_reading_time(words, words_per_minute=100)
        assert slow > fast


class TestExtractExcerpt:
    """Tests for extract_excerpt function."""

    def test_returns_first_paragraph(self):
        """Test returns first paragraph content."""
        content = "First paragraph here.\n\nSecond paragraph."
        result = extract_excerpt(content)
        assert "First paragraph" in result

    def test_truncates_long_content(self):
        """Test long content is truncated."""
        content = "word " * 200
        result = extract_excerpt(content, max_length=50)
        assert len(result) <= 60  # Some slack for ellipsis

    def test_adds_ellipsis_on_truncation(self):
        """Test truncated content ends with ellipsis."""
        content = "word " * 100
        result = extract_excerpt(content, max_length=20)
        assert result.endswith("...")


class TestExtractTableOfContents:
    """Tests for extract_table_of_contents function."""

    def test_extracts_headings(self):
        """Test all heading levels are extracted."""
        content = "# H1\n## H2\n### H3"
        toc = extract_table_of_contents(content)
        assert len(toc) == 3

    def test_correct_levels(self):
        """Test heading levels are correct."""
        content = "# H1\n## H2\n### H3"
        toc = extract_table_of_contents(content)
        assert toc[0]["level"] == 1
        assert toc[1]["level"] == 2
        assert toc[2]["level"] == 3

    def test_generates_anchors(self):
        """Test anchor IDs are generated."""
        content = "# My Heading"
        toc = extract_table_of_contents(content)
        assert "anchor" in toc[0]
        assert "my" in toc[0]["anchor"]

    def test_empty_content_returns_empty(self):
        """Test empty content returns empty TOC."""
        toc = extract_table_of_contents("")
        assert toc == []
