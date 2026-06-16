"""Parse product formulations and enrich each ingredient via INCI + PubChem/PubMed."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django.db import IntegrityError, transaction

from literature.enrichment.compound_bootstrap import apply_entity_classification
from literature.ingestion import inci_client
from literature.ingestion.inci_ingest import ingest_inci_ingredient
from literature.ingestion.ingest import ingest_compound
from core.models import (
    Compound,
    CompoundAlias,
    EnrichmentStatus,
    Formulation,
    FormulationIngredient,
)
from core.models.brand import Brand
from core.models.product import Product

logger = logging.getLogger(__name__)


@dataclass
class IngredientIngestResult:
    name: str
    position: int
    compound_id: int | None = None
    parse_status: str = "unmatched"
    inci_properties: int = 0
    pubchem_descriptors: int = 0
    articles_linked: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class FormulationIngestResult:
    formulation_id: int
    product_name: str
    ingredient_count: int
    enrichment_status: str = EnrichmentStatus.PENDING
    ingredients: list[IngredientIngestResult] = field(default_factory=list)


@dataclass
class BarcodeScanResult:
    formulation_id: int
    product_id: int
    barcode: str
    ingredient_count: int
    created: bool
    errors: list[str] = field(default_factory=list)


def ingest_product_by_barcode(barcode: str) -> BarcodeScanResult:
    """Fetch a product from the INCI API by barcode and persist it.

    Cache-first: if a Formulation with this barcode already exists it is
    returned immediately (created=False) without calling the API.

    Raises:
        ValueError: if the barcode is not found in the INCI API (HTTP 404).
        HttpError: for upstream API errors other than 404.
    """
    # Cache-first: return existing formulation if already ingested.
    existing = _get_barcode_formulation(barcode)
    if existing is not None:
        return _barcode_scan_result(existing, barcode=barcode, created=False)

    product_data = inci_client.get_product(barcode)
    if product_data is None:
        raise ValueError(f"Barcode {barcode} not found")

    errors: list[str] = []

    try:
        with transaction.atomic():
            # Re-check inside the write transaction for requests that completed while
            # this scan was waiting on the upstream product lookup.
            existing = _get_barcode_formulation(barcode)
            if existing is not None:
                return _barcode_scan_result(existing, barcode=barcode, created=False)

            product_obj = _get_or_create_inci_product(product_data, barcode=barcode)

            # Create Formulation.
            formulation = Formulation.objects.create(
                product=product_obj,
                barcode=barcode,
                raw_inci_text=product_data.ingredients_text,
                made_in=product_data.country,
                source="inciapi",
                source_ref=f"inciapi:barcode:{barcode}",
                enrichment_status=EnrichmentStatus.PENDING,
                inci_analysis=product_data.analysis if product_data.analysis else None,
            )

            # Create FormulationIngredient rows for each INCI name.
            inci_names = product_data.inci_list
            # Fall back to parsing the raw text if inci_list is empty.
            if not inci_names and product_data.ingredients_text:
                inci_names = parse_inci_list(product_data.ingredients_text)

            for position, inci_name in enumerate(inci_names, start=1):
                name = inci_name.strip()
                if not name:
                    continue
                try:
                    compound, parse_status = resolve_compound(name)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Could not resolve compound %r: %s", name, exc)
                    compound = None
                    parse_status = "unmatched"
                    errors.append(f"compound:{name}:{exc}")
                FormulationIngredient.objects.create(
                    formulation=formulation,
                    position=position,
                    raw_text=name,
                    compound=compound,
                    parse_status=parse_status,
                )
    except IntegrityError:
        existing = _get_barcode_formulation(barcode)
        if existing is None:
            raise
        logger.info("Barcode %s was created by a concurrent scan", barcode)
        return _barcode_scan_result(existing, barcode=barcode, created=False)

    # After the transaction commits, enqueue async enrichment.
    from core.tasks import enrich_formulation_ingredients  # avoid circular import
    enrich_formulation_ingredients.delay(formulation.pk)

    return BarcodeScanResult(
        formulation_id=formulation.pk,
        product_id=product_obj.pk,
        barcode=barcode,
        ingredient_count=len(inci_names),
        created=True,
        errors=errors,
    )


def _get_barcode_formulation(barcode: str) -> Formulation | None:
    return Formulation.objects.filter(barcode=barcode).first()


def _get_or_create_brand(name: str) -> Brand | None:
    cleaned = name.strip()
    if not cleaned:
        return None

    try:
        with transaction.atomic():
            return Brand.get_or_create_by_name(cleaned)
    except IntegrityError:
        return Brand.objects.filter(name__iexact=cleaned).first()


def _get_or_create_inci_product(product_data: InciProduct, *, barcode: str) -> Product:
    brand_obj = _get_or_create_brand(product_data.brand)
    product_name = product_data.name.strip() or "Unnamed product"
    product_obj = Product.objects.filter(
        brand=brand_obj,
        name__iexact=product_name,
    ).first()
    if product_obj is not None:
        return product_obj

    try:
        with transaction.atomic():
            return Product.objects.create(
                brand=brand_obj,
                name=product_name,
                display_name=product_name,
                category=product_data.category,
                image_url=product_data.image_url,
                source="inciapi",
                source_ref=f"inciapi:barcode:{barcode}",
            )
    except IntegrityError:
        product_obj = Product.objects.filter(
            brand=brand_obj,
            name__iexact=product_name,
        ).first()
        if product_obj is None:
            raise
        return product_obj


def _barcode_scan_result(
    formulation: Formulation,
    *,
    barcode: str,
    created: bool,
) -> BarcodeScanResult:
    return BarcodeScanResult(
        formulation_id=formulation.pk,
        product_id=formulation.product_id,
        barcode=barcode,
        ingredient_count=formulation.ingredients.count(),
        created=created,
    )


def parse_inci_list(text: str) -> list[str]:
    """Split a raw INCI declaration into ordered, deduplicated ingredient names."""
    if not text.strip():
        return []

    normalized = text.replace("\n", ",").replace(";", ",")
    parts = [part.strip() for part in normalized.split(",")]

    seen: set[str] = set()
    ingredients: list[str] = []
    for part in parts:
        name = _normalize_ingredient_token(part)
        if not name:
            continue
        key = name.upper()
        if key in seen:
            continue
        seen.add(key)
        ingredients.append(name)
    return ingredients


def _normalize_ingredient_token(token: str) -> str:
    token = token.strip().rstrip(".")
    if not token:
        return ""
    if "(" in token:
        token = token.split("(", 1)[0].strip()
    return token


def resolve_compound(name: str) -> tuple[Compound, str]:
    """Match an ingredient to an existing compound or create a new one."""
    canonical = " ".join(name.upper().split())

    compound = Compound.objects.filter(canonical_inci=canonical).first()
    if compound:
        return compound, "matched"

    alias = (
        CompoundAlias.objects.filter(alias_text__iexact=name.strip())
        .select_related("compound")
        .first()
    )
    if alias:
        return alias.compound, "matched"

    compound = Compound.objects.create(
        canonical_inci=canonical,
        display_name=name.strip(),
    )
    classification = apply_entity_classification(
        compound,
        asserted_by="formulation_ingest",
    )
    from core.models import EntityType
    from core.models.literature_discovery_target import DiscoveryReason
    from literature.discovery import enqueue_literature_discovery_for_compound

    reason = (
        DiscoveryReason.NEW_MIXTURE
        if classification.entity_type == EntityType.MIXTURE
        else DiscoveryReason.NEW_COMPOUND
    )
    enqueue_literature_discovery_for_compound(
        compound,
        reason,
        triggered_by="formulation_ingest",
        source_ref=f"resolve_compound:{canonical}",
    )
    return compound, "unmatched"


def create_formulation(
    product_name: str,
    raw_inci_text: str,
    *,
    brand: str = "",
) -> Formulation:
    """Persist a formulation and parsed ingredient rows without running enrichment."""
    ingredient_names = parse_inci_list(raw_inci_text)
    product = _get_or_create_product(product_name, brand=brand)
    formulation = Formulation.objects.create(
        product=product,
        raw_inci_text=raw_inci_text.strip(),
        source="frontend",
        enrichment_status=EnrichmentStatus.PENDING,
    )

    for position, name in enumerate(ingredient_names, start=1):
        compound, parse_status = resolve_compound(name)
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=position,
            raw_text=name,
            compound=compound,
            parse_status=parse_status,
        )

    return formulation


def _get_or_create_product(product_name: str, *, brand: str = "") -> Product:
    name = product_name.strip() or "Unnamed product"
    brand_obj = Brand.get_or_create_by_name(brand)
    product = Product.objects.filter(
        brand=brand_obj,
        name__iexact=name,
    ).first()
    if product is not None:
        return product
    return Product.objects.create(
        brand=brand_obj,
        name=name,
        display_name=name,
        source="frontend",
    )


def ingest_formulation_ingredients(
    formulation_id: int,
    *,
    with_pubmed: bool = True,
    max_articles: int = 5,
) -> FormulationIngestResult:
    """Run INCI + PubChem/PubMed ingestion for every ingredient on a formulation."""
    formulation = (
        Formulation.objects.select_related("product__brand")
        .prefetch_related("ingredients__compound")
        .get(pk=formulation_id)
    )
    results: list[IngredientIngestResult] = []

    for row in formulation.ingredients.all():
        ingredient_result = _ingest_ingredient(
            row,
            with_pubmed=with_pubmed,
            max_articles=max_articles,
        )
        results.append(ingredient_result)

    _finalize_formulation_status(formulation)
    formulation.refresh_from_db()

    return FormulationIngestResult(
        formulation_id=formulation.pk,
        product_name=formulation.product.name,
        ingredient_count=len(results),
        enrichment_status=formulation.enrichment_status,
        ingredients=results,
    )


def ingest_formulation(
    product_name: str,
    raw_inci_text: str,
    *,
    brand: str = "",
    with_pubmed: bool = True,
    max_articles: int = 5,
) -> FormulationIngestResult:
    """Create a formulation and enrich all ingredients in one call."""
    formulation = create_formulation(product_name, raw_inci_text, brand=brand)
    return ingest_formulation_ingredients(
        formulation.pk,
        with_pubmed=with_pubmed,
        max_articles=max_articles,
    )


def _ingest_ingredient(
    row: FormulationIngredient,
    *,
    with_pubmed: bool,
    max_articles: int,
) -> IngredientIngestResult:
    name = row.raw_text
    compound = row.compound
    result = IngredientIngestResult(
        name=name,
        position=row.position,
        compound_id=compound.pk if compound else None,
        parse_status=row.parse_status,
    )

    if compound is None:
        compound, parse_status = resolve_compound(name)
        row.compound = compound
        row.parse_status = parse_status
        row.save(update_fields=["compound", "parse_status"])
        result.compound_id = compound.pk
        result.parse_status = parse_status

    inci_result = ingest_inci_ingredient(
        name,
        asserted_by="formulation_ingest",
    )
    result.inci_properties = inci_result.properties_written
    result.errors.extend(inci_result.errors)

    compound_result = ingest_compound(
        name,
        with_pubmed=with_pubmed,
        max_articles=max_articles,
        max_related=3,
        asserted_by="formulation_ingest",
    )
    result.pubchem_descriptors = compound_result.descriptors_written
    result.articles_linked = compound_result.articles_linked
    result.errors.extend(compound_result.errors)

    if not result.errors and row.parse_status == "unmatched":
        row.parse_status = "matched"
        row.save(update_fields=["parse_status"])

    return result


def _finalize_formulation_status(formulation: Formulation) -> None:
    ingredients = list(formulation.ingredients.select_related("compound"))
    if not ingredients:
        formulation.enrichment_status = EnrichmentStatus.PENDING
        formulation.save(update_fields=["enrichment_status", "updated_at"])
        return

    compounds = [row.compound for row in ingredients if row.compound_id]
    if not compounds:
        formulation.enrichment_status = EnrichmentStatus.PENDING
    else:
        statuses = {compound.enrichment_status for compound in compounds}
        if statuses == {EnrichmentStatus.COMPLETE}:
            formulation.enrichment_status = EnrichmentStatus.COMPLETE
        elif EnrichmentStatus.COMPLETE in statuses or EnrichmentStatus.PARTIAL in statuses:
            formulation.enrichment_status = EnrichmentStatus.PARTIAL
        elif EnrichmentStatus.NEEDS_REVIEW in statuses:
            formulation.enrichment_status = EnrichmentStatus.NEEDS_REVIEW
        else:
            formulation.enrichment_status = EnrichmentStatus.PARTIAL

    formulation.save(update_fields=["enrichment_status", "updated_at"])
