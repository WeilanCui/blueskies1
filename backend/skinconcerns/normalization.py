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
        "cant",
        "cannot",
        # Normalized contraction stems, e.g. "don't" -> "don t".
        "don",
        "doesn",
        "didn",
        "isn",
        "aren",
        "wasn",
        "weren",
        "haven",
        "hasn",
        "hadn",
        "won",
        "wouldn",
        "couldn",
        "shouldn",
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

CONNECTOR_TOKENS = frozenset(
    {
        "of",
        "from",
        "with",
        "for",
        "to",
        "in",
        "on",
        "at",
        "by",
        "about",
        "sign",
        "signs",
        "symptom",
        "symptoms",
        "have",
        "has",
        "had",
        "having",
        "get",
        "gets",
        "got",
        "getting",
        "experience",
        "experiences",
        "experiencing",
        "suffer",
        "suffers",
        "suffering",
        "see",
        "sees",
        "seeing",
        "saw",
        "notice",
        "notices",
        "noticing",
        "noticed",
        "show",
        "shows",
        "showing",
        "shown",
        "t",
    }
)

NEGATION_LOOKBACK_LIMIT = 6


def normalize_search_text(value: str) -> str:
    """Normalize user concern text for exact alias lookup."""
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _phrase_is_negated(text_tokens: list[str], start_index: int) -> bool:
    """Return True when a phrase match is preceded by negation."""
    if start_index == 0:
        return False

    skippable = SKIP_TOKENS | CONNECTOR_TOKENS
    index = start_index - 1
    steps = 0
    while index >= 0 and steps < NEGATION_LOOKBACK_LIMIT:
        token = text_tokens[index]
        if token in NEGATION_TOKENS:
            return True
        if token not in skippable:
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
