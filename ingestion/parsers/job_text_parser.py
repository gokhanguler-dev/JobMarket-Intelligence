import html
import re


def clean_html_text(text):
    """
    Cleans HTML tags/entities and unnecessary whitespace
    from job posting text.
    """

    if not text:
        return None

    # Convert HTML entities:
    # &nbsp; -> space
    # &amp;  -> &
    text = html.unescape(text)

    # Remove HTML tags:
    # <b>Data</b> -> Data
    text = re.sub(r"<[^>]+>", "", text)

    # Replace non-breaking spaces
    text = text.replace("\xa0", " ")

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()