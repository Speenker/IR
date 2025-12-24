from __future__ import annotations

from bs4 import BeautifulSoup


def extract_text_from_html(html_utf8: str) -> str:
    soup = BeautifulSoup(html_utf8, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())
