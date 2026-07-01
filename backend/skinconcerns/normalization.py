import re


def normalize_search_text(value: str) -> str:
    """Normalize user concern text for exact alias lookup."""
    text = re.sub(r"[^a-z0-9]+", " ", value.casefold())
    return " ".join(text.split())


def normalized_phrase_in_text(phrase: str, text: str) -> bool:
    """Return True when normalized phrase tokens appear consecutively in text."""
    phrase_tokens = normalize_search_text(phrase).split()
    text_tokens = normalize_search_text(text).split()
    if not phrase_tokens or len(phrase_tokens) > len(text_tokens):
        return False

    phrase_len = len(phrase_tokens)
    for index in range(len(text_tokens) - phrase_len + 1):
        if text_tokens[index : index + phrase_len] == phrase_tokens:
            return True
    return False
