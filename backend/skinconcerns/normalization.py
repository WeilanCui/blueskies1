import re


def normalize_search_text(value: str) -> str:
    """Normalize user concern text for exact alias lookup."""
    text = re.sub(r"[^a-z0-9]+", " ", value.casefold())
    return " ".join(text.split())
