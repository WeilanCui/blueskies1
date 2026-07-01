import re
import unicodedata


NEGATION_TOKENS = frozenset(
    {
        "no",
        "not",
        "without",
        "never",
        "neither",
        "nor",
        "none",
        "hardly",
        "barely",
        "scarcely",
    }
)

SKIP_TOKENS = frozenset(
    {
        "a",
        "an",
        "the",
        "any",
        "my",
        "your",
        "their",
        "his",
        "her",
        "its",
        "our",
        "this",
        "that",
        "some",
    }
)


def normalize_search_text(value: str) -> str:
    """Normalize user concern text for exact alias lookup."""
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _phrase_is_negated(text_tokens: list[str], start_index: int) -> bool:
    """Return True when a phrase match is immediately preceded by negation."""
    if start_index == 0:
        return False

    index = start_index - 1
    steps = 0
    while index >= 0 and steps < 3:
        token = text_tokens[index]
        if token in NEGATION_TOKENS:
            return True
        if token not in SKIP_TOKENS:
            break
        index -= 1
        steps += 1
    return False


def normalized_phrase_in_text(phrase: str, text: str) -> bool:
    """Return True when normalized phrase tokens appear consecutively in text."""
    phrase_tokens = normalize_search_text(phrase).split()
    text_tokens = normalize_search_text(text).split()
    if not phrase_tokens or len(phrase_tokens) > len(text_tokens):
        return False

    phrase_len = len(phrase_tokens)
    for index in range(len(text_tokens) - phrase_len + 1):
        if text_tokens[index : index + phrase_len] != phrase_tokens:
            continue
        if not _phrase_is_negated(text_tokens, index):
            return True
    return False
