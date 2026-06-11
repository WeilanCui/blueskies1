"""LLM and offline extractors for literature enrichment."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from django.conf import settings

from literature.ingestion.relevance import classify_relevance, infer_role_in_paper
from core.models import RelevanceCategory, RoleInPaper
from literature.seeds.property_definitions import FUNCTIONAL_CLASS_VALUES

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {choice.value for choice in RelevanceCategory}
VALID_ROLES = {choice.value for choice in RoleInPaper}
VALID_FUNCTIONAL_CLASSES = set(FUNCTIONAL_CLASS_VALUES)


@dataclass
class LiteratureExtraction:
    relevance_category: str
    role_in_paper: str
    functional_classes: list[str] = field(default_factory=list)
    evidence_summary: str = ""
    confidence: float = 0.5


@dataclass
class ExtractionContext:
    inci_name: str
    title: str
    abstract: str
    mesh_terms: list[str] = field(default_factory=list)


class LiteratureExtractor(ABC):
    name: str = "base"

    @abstractmethod
    def extract(self, context: ExtractionContext) -> LiteratureExtraction:
        """Return structured enrichment from title/abstract context."""


# Keyword cues for offline functional-class inference (first match per class).
_FUNCTIONAL_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("preservative", ("preservative", "antimicrobial", "antibacterial", "antifungal")),
    ("humectant", ("humectant",)),
    ("solvent", ("solvent", "vehicle")),
    ("emollient", ("emollient",)),
    ("antioxidant", ("antioxidant",)),
    ("surfactant", ("surfactant", "detergent")),
    ("emulsifier", ("emulsifier", "emulsif")),
    ("solubilizer", ("solubilizer",)),
    ("active", ("active ingredient", "active compound")),
]


def _infer_functional_classes(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for functional_class, keywords in _FUNCTIONAL_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            found.append(functional_class)
    return found


def _validate_extraction(data: dict) -> LiteratureExtraction:
    category = data.get("relevance_category", RelevanceCategory.GENERAL)
    if category not in VALID_CATEGORIES:
        category = RelevanceCategory.GENERAL

    role = data.get("role_in_paper", RoleInPaper.UNKNOWN)
    if role not in VALID_ROLES:
        role = RoleInPaper.UNKNOWN

    classes = data.get("functional_classes", [])
    if isinstance(classes, str):
        classes = [classes]
    classes = [
        value
        for value in classes
        if isinstance(value, str) and value in VALID_FUNCTIONAL_CLASSES
    ]

    confidence = data.get("confidence", 0.5)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    evidence = str(data.get("evidence_summary", "")).strip()

    return LiteratureExtraction(
        relevance_category=category,
        role_in_paper=role,
        functional_classes=classes,
        evidence_summary=evidence,
        confidence=confidence,
    )


class StubExtractor(LiteratureExtractor):
    """Deterministic offline extractor for tests and environments without an API key."""

    name = "stub"

    def extract(self, context: ExtractionContext) -> LiteratureExtraction:
        combined = " ".join(
            [context.title, context.abstract, " ".join(context.mesh_terms)]
        )
        category = classify_relevance(
            context.mesh_terms, context.title, context.abstract
        )
        role = infer_role_in_paper(
            context.inci_name, context.title, context.abstract
        )
        functional_classes = _infer_functional_classes(combined)
        confidence = 0.55 if functional_classes else 0.45
        summary = (
            f"Stub enrichment for {context.inci_name}: "
            f"{category} / {role}"
            + (f"; functional={','.join(functional_classes)}" if functional_classes else "")
        )
        return LiteratureExtraction(
            relevance_category=category,
            role_in_paper=role,
            functional_classes=functional_classes,
            evidence_summary=summary,
            confidence=confidence,
        )


class OpenAIExtractor(LiteratureExtractor):
    """OpenAI Chat Completions JSON extractor."""

    name = "openai"

    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIExtractor")

    def extract(self, context: ExtractionContext) -> LiteratureExtraction:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        system_prompt = _build_system_prompt()
        user_prompt = _build_user_prompt(context)
        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content or "{}"
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenAI returned invalid JSON: {exc}") from exc
        return _validate_extraction(payload)


def _build_system_prompt() -> str:
    categories = ", ".join(sorted(VALID_CATEGORIES))
    roles = ", ".join(sorted(VALID_ROLES))
    classes = ", ".join(sorted(VALID_FUNCTIONAL_CLASSES))
    return (
        "You extract structured cosmetic-ingredient evidence from PubMed abstracts. "
        "Return JSON with keys: relevance_category, role_in_paper, functional_classes "
        "(array), evidence_summary (short quote or paraphrase), confidence (0-1). "
        f"relevance_category must be one of: {categories}. "
        f"role_in_paper must be one of: {roles}. "
        f"functional_classes values must be from: {classes}. "
        "functional_classes describes what the ingredient IS in context (e.g. preservative), "
        "not the study design role. Use an empty array when unclear."
    )


def _build_user_prompt(context: ExtractionContext) -> str:
    mesh = ", ".join(context.mesh_terms) if context.mesh_terms else "(none)"
    return (
        f"INCI/compound: {context.inci_name}\n"
        f"Title: {context.title}\n"
        f"Abstract: {context.abstract}\n"
        f"MeSH: {mesh}"
    )


def get_extractor(mode: str | None = None) -> LiteratureExtractor:
    """Factory: auto (OpenAI if key present else stub), stub, or openai."""
    selected = (mode or settings.LITERATURE_EXTRACTOR or "auto").lower()
    if selected == "stub":
        return StubExtractor()
    if selected == "openai":
        return OpenAIExtractor()
    if selected == "auto":
        if settings.OPENAI_API_KEY:
            return OpenAIExtractor()
        return StubExtractor()
    raise ValueError(f"Unknown literature extractor mode: {selected!r}")
