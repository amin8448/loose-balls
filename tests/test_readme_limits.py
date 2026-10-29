"""README.md: at most 1,000 words (markdown stripped, figure captions and code counted) and at
most two figures or tables in total (Analytics Cup 2.0 call for papers)."""

import re
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"
MAX_WORDS, MAX_FIGURES_AND_TABLES = 1000, 2


def words(markdown: str) -> int:
    text = re.sub(r"<!--.*?-->", " ", markdown, flags=re.DOTALL)  # comments are not shown
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r" \1 ", text)  # image: keep the caption (alt text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r" \1 ", text)  # link: keep the text, drop the URL
    text = re.sub(r"<img[^>]*alt=\"([^\"]*)\"[^>]*>", r" \1 ", text)
    text = re.sub(r"<[^>]+>", " ", text)  # other HTML tags
    text = re.sub(r"^\s*\|?\s*:?-{3,}.*$", " ", text, flags=re.MULTILINE)  # table separator rows
    text = re.sub(r"[#*_`>|~]", " ", text)
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9.,%'/:+\-]*", text))


def figures_and_tables(markdown: str) -> int:
    images = len(re.findall(r"!\[[^\]]*\]\([^)]*\)", markdown)) + len(re.findall(r"<img\b", markdown))
    tables = len(re.findall(r"^\s*\|?\s*:?-{3,}:?\s*\|", markdown, flags=re.MULTILINE))
    return images + tables


def test_counting_rules():
    sample = "# Title\n\nTwo words [here](http://x.y/z).\n\n![A caption of five](f.png)\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    assert words(sample) == 12  # Title, Two, words, here, four caption words, a, b, 1, 2
    assert figures_and_tables(sample) == 2


def test_readme_within_limits():
    text = README.read_text()
    assert words(text) <= MAX_WORDS, f"README has {words(text)} words"
    assert figures_and_tables(text) <= MAX_FIGURES_AND_TABLES
