"""User-experience relevance: PubMed query building, category + role classification."""

from __future__ import annotations

from literature.models import RelevanceCategory, RoleInPaper

# PubMed clauses that scope results to user-experience-relevant literature.
# The cosmetics/preservatives clauses are what capture formulation-context papers
# (e.g. a compound used only as a solvent) that adverse-effect filters would miss.
_UX_CLAUSES = [
    "adverse effects[sh]",
    "toxicity[sh]",
    '"Dermatitis, Allergic Contact"[mesh]',
    "Irritants[mesh]",
    "cosmetics[mesh]",
    '"Preservatives, Pharmaceutical"[mesh]',
    "skin[tiab]",
    "safety[tiab]",
    "tolerability[tiab]",
]


def build_ux_query(name: str) -> str:
    """Build a PubMed query scoping a compound to user-experience relevance."""
    clause = " OR ".join(_UX_CLAUSES)
    return f'"{name}"[All Fields] AND ({clause})'


# Ordered keyword -> category rules. First match wins; more specific first.
_CATEGORY_RULES: list[tuple[RelevanceCategory, tuple[str, ...]]] = [
    (
        RelevanceCategory.SENSITIZATION,
        (
            "allergic contact",
            "sensitization",
            "sensitisation",
            "allergen",
            "hypersensitivity",
            "patch test",
        ),
    ),
    (
        RelevanceCategory.IRRITATION,
        ("irritant", "irritation", "stinging"),
    ),
    (
        RelevanceCategory.SIDE_EFFECT,
        (
            "adverse",
            "side effect",
            "dermatitis",
            "erythema",
            "phototoxicity",
            "cytotoxic",
        ),
    ),
    (
        RelevanceCategory.PRESERVATION_PERFORMANCE,
        (
            "preservative",
            "preservatives",
            "antimicrobial",
            "antibacterial",
            "antifungal",
            "microbial sensitivity",
            "minimum inhibitory",
            "challenge test",
        ),
    ),
    (
        RelevanceCategory.STABILITY,
        ("stability", "shelf life", "shelf-life", "degradation", "accelerated stability"),
    ),
    (
        RelevanceCategory.SAFETY_PROFILE,
        ("safety", "tolerability", "biocompatibility", "no observed adverse"),
    ),
    (
        RelevanceCategory.EFFICACY,
        (
            "efficacy",
            "antioxidant",
            "moisturizing",
            "moisturising",
            "hydration",
            "anti-aging",
            "anti-ageing",
            "whitening",
            "brightening",
        ),
    ),
    (
        RelevanceCategory.INTERACTION,
        ("synergy", "synergistic", "combination", "interaction"),
    ),
]


def classify_relevance(
    mesh_terms: list[str] | None,
    title: str = "",
    abstract: str = "",
) -> RelevanceCategory:
    """Map MeSH terms + title/abstract keywords to a relevance category."""
    haystack = " ".join(
        [t.lower() for t in (mesh_terms or [])]
        + [title.lower(), abstract.lower()]
    )
    for category, keywords in _CATEGORY_RULES:
        if any(kw in haystack for kw in keywords):
            return category
    return RelevanceCategory.GENERAL


# Phrases that indicate the compound is a vehicle/solvent rather than the subject.
_SOLVENT_CUES = (
    "as a solvent",
    "as solvent",
    "dispersed in",
    "dissolved in",
    "diluted in",
    "as the vehicle",
    "as vehicle",
    "in {name}",
    "{name} in water",
    "{name} solution",
)

_CO_INGREDIENT_CUES = (
    "combined with",
    "in combination with",
    "formulated with",
    "co-formulated",
    "addition of",
)

_COMPARATOR_CUES = ("compared to", "compared with", "versus", "in comparison")


def infer_role_in_paper(name: str, title: str = "", abstract: str = "") -> RoleInPaper:
    """Infer whether the compound is the subject, a solvent, co-ingredient, etc.

    Keeps a solvent mention (e.g. 1,2-hexanediol used to dissolve another extract)
    from being mis-scored as a safety study of that compound.
    """
    name_l = name.lower()
    text = f"{title} {abstract}".lower()
    if not text.strip():
        return RoleInPaper.UNKNOWN

    for cue in _SOLVENT_CUES:
        phrase = cue.format(name=name_l)
        if phrase in text:
            return RoleInPaper.SOLVENT

    for cue in _COMPARATOR_CUES:
        if cue in text:
            return RoleInPaper.COMPARATOR

    for cue in _CO_INGREDIENT_CUES:
        if cue in text:
            return RoleInPaper.CO_INGREDIENT

    # Compound named in the title -> likely the primary subject.
    if name_l in title.lower():
        return RoleInPaper.SUBJECT

    return RoleInPaper.UNKNOWN
