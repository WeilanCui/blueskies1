"""INCI pattern classifier for entity type and structure resolvability."""

from dataclasses import dataclass, field
import re


@dataclass(frozen=True)
class EntityClassification:
    entity_type: str
    structure_resolvable: bool
    confidence: float
    reason: str
    suggested_functional_classes: list[str] = field(default_factory=list)


FRAGRANCE_INCI = frozenset(
    {
        "PARFUM",
        "FRAGRANCE",
        "AROMA",
        "FLAVOR",
        "FLAVOUR",
    }
)

POLYMER_MARKERS = (
    "CARBOMER",
    "CROSSPOLYMER",
    "COPOLYMER",
    "XANTHAN GUM",
    "HYDROXYETHYLCELLULOSE",
    "HYDROXYPROPYLCELLULOSE",
    "CELLULOSE GUM",
    "ACRYLATES",
)

SILICONE_MARKERS = (
    "DIMETHICONE",
    "METHICONE",
    "SILOXANE",
    "SILSESQUIOXANE",
    "TRISILOXANE",
)

BOTANICAL_MARKERS = (
    " EXTRACT",
    " JUICE",
    " LEAF ",
    " FLOWER ",
    " ROOT ",
    " SEED ",
    " BARK ",
    " FRUIT ",
    " WATER",
)

UVCB_MARKERS = (
    "PETROLATUM",
    "MINERAL OIL",
    "PARAFFINUM LIQUIDUM",
    "CERA MICROCRISTALLINA",
    "MICROCRYSTALLINE WAX",
)


def _normalize(inci: str) -> str:
    return " ".join(inci.upper().split())


def classify_inci(inci: str) -> EntityClassification:
    """
    Classify a single INCI name before PubChem resolution.

    Priority: fragrance_blend > mineral > silicone > polymer > botanical >
    uvcb > mixture (proprietary blend hints) > small_molecule heuristic.
    """
    name = _normalize(inci)
    if not name:
        return EntityClassification(
            entity_type="unknown",
            structure_resolvable=False,
            confidence=0.0,
            reason="Empty INCI",
        )

    if name in FRAGRANCE_INCI or name.startswith("PARFUM/"):
        return EntityClassification(
            entity_type="fragrance_blend",
            structure_resolvable=False,
            confidence=0.99,
            reason="INCI fragrance umbrella term; composition not disclosed.",
            suggested_functional_classes=["fragrance"],
        )

    if name.startswith("CI ") or re.match(r"^CI\s*\d", name):
        return EntityClassification(
            entity_type="mineral",
            structure_resolvable=False,
            confidence=0.95,
            reason="Color Index pigment or mineral colorant.",
            suggested_functional_classes=["colorant"],
        )

    for marker in SILICONE_MARKERS:
        if marker in name:
            return EntityClassification(
                entity_type="silicone",
                structure_resolvable=False,
                confidence=0.9,
                reason=f"Silicone INCI pattern ({marker}).",
                suggested_functional_classes=["emollient", "occlusive"],
            )

    for marker in POLYMER_MARKERS:
        if marker in name:
            return EntityClassification(
                entity_type="polymer",
                structure_resolvable=False,
                confidence=0.9,
                reason=f"Polymer/rheology INCI pattern ({marker}).",
                suggested_functional_classes=["thickener_rheology_modifier"],
            )

    for marker in BOTANICAL_MARKERS:
        if marker in name or name.endswith(" OIL"):
            return EntityClassification(
                entity_type="botanical_extract",
                structure_resolvable=False,
                confidence=0.85,
                reason="Botanical source INCI; complex composition without single SMILES.",
            )

    for marker in UVCB_MARKERS:
        if marker in name:
            return EntityClassification(
                entity_type="uvcb",
                structure_resolvable=False,
                confidence=0.9,
                reason="REACH-style UVCB petroleum or variable-composition material.",
                suggested_functional_classes=["occlusive", "emollient"],
            )

    if " EXTRACT BLEND" in name or " COMPLEX" in name or " BLEND" in name:
        return EntityClassification(
            entity_type="mixture",
            structure_resolvable=False,
            confidence=0.8,
            reason="Proprietary or multi-component blend INCI wording.",
        )

    if name == "AQUA" or name == "WATER":
        return EntityClassification(
            entity_type="small_molecule",
            structure_resolvable=True,
            confidence=1.0,
            reason="Water; single definable structure.",
            suggested_functional_classes=["solvent", "excipient_base"],
        )

    if len(name) < 64 and "/" not in name and " AND " not in name:
        return EntityClassification(
            entity_type="small_molecule",
            structure_resolvable=True,
            confidence=0.6,
            reason="Single-component INCI; confirm with CAS/PubChem before enrichment.",
        )

    return EntityClassification(
        entity_type="unknown",
        structure_resolvable=False,
        confidence=0.3,
        reason="No pattern match; needs manual or PubChem resolution.",
    )
