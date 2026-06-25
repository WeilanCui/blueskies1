"""Tests for INCI API client, mapping, ingestion, and provenance."""

from unittest import mock

from django.test import SimpleTestCase, TestCase

from literature.enrichment.provenance import assert_property
from literature.ingestion import inci_client, ingest_inci_ingredient
from literature.ingestion.http import HttpError
from literature.ingestion.inci_client import InciIngredient, parse_ingredient
from literature.ingestion.inci_ingest import map_ingredient
from core.models import (
    Compound,
    CompoundAlias,
    CompoundIdentifier,
    PropertyAssertion,
    PropertyDefinition,
    SourceType,
)
from literature.seeds.loader import upsert_property_definitions

RETINOL_RAW = {
    "inciName": "Retinol",
    "aliases": ["Vitamin A", "Retinyl Alcohol"],
    "casNumber": "68-26-8",
    "ecNumber": "200-683-7",
    "description": "A vitamin A derivative used in anti-aging products.",
    "functions": ["ANTIOXIDANT", "SKIN CONDITIONING", "BRIGHTENING"],
    "safetyScore": 6.5,
    "safetyLevel": "moderate",
    "isEuAllergen": False,
    "allergenTypes": [],
    "comedogenicityRating": 1,
    "irritancyPotential": "moderate",
    "suitableForSkinTypes": ["normal", "dry"],
    "avoidForSkinTypes": ["sensitive"],
    "pregnancySafe": "caution",
    "euStatus": "allowed",
    "photosensitivityRisk": "high",
    "stability": "unstable",
    "optimalPhRange": "5.0-6.0",
    "evidenceQuality": 4,
}

NIACINAMIDE_RAW = {
    "inciName": "Niacinamide",
    "aliases": ["Nicotinamide"],
    "casNumber": "98-92-0",
    "functions": ["HUMECTANT", "ANTI-ACNE", "SKIN BRIGHTENING"],
    "safetyScore": 8.0,
    "isEuAllergen": False,
    "comedogenicityRating": 0,
    "irritancyPotential": "none",
    "pregnancySafe": "safe",
    "euStatus": "allowed",
    "evidenceQuality": 5,
}


class InciParsingTests(SimpleTestCase):
    def test_parse_retinol_fixture(self):
        ingredient = parse_ingredient(RETINOL_RAW)
        self.assertEqual(ingredient.inci_name, "Retinol")
        self.assertEqual(ingredient.cas_number, "68-26-8")
        self.assertEqual(ingredient.comedogenicity_rating, 1)
        self.assertEqual(ingredient.evidence_quality, 4)
        self.assertEqual(ingredient.raw["inciName"], "Retinol")

    def test_parse_niacinamide_fixture(self):
        ingredient = parse_ingredient(NIACINAMIDE_RAW)
        self.assertEqual(ingredient.inci_name, "Niacinamide")
        self.assertEqual(ingredient.safety_score, 8.0)
        self.assertFalse(ingredient.is_eu_allergen)


class InciMappingTests(SimpleTestCase):
    def test_retinol_mapping_coercions(self):
        ingredient = parse_ingredient(RETINOL_RAW)
        claims = {c.key: c for c in map_ingredient(ingredient)}

        self.assertEqual(
            sorted(claims["functional_class"].value_json),  # pyright: ignore[reportArgumentType]
            ["antioxidant", "emollient"],
        )
        self.assertEqual(claims["comedogenic_risk"].value_text, "low")
        self.assertEqual(claims["irritation_potential"].value_text, "moderate")
        self.assertEqual(claims["sensitization_potential"].value_text, "unknown")
        self.assertEqual(
            claims["ph_stability_range"].value_json, {"min": 5.0, "max": 6.0}
        )
        self.assertTrue(claims["light_sensitive"].value_bool)
        self.assertTrue(claims["oxidation_sensitive"].value_bool)
        self.assertEqual(claims["evidence_strength"].value_text, "moderate")
        self.assertEqual(claims["pregnancy_safe"].value_text, "caution")
        self.assertEqual(claims["eu_regulatory_status"].value_text, "allowed")
        self.assertEqual(claims["inci_safety_score"].value_numeric, 6.5)
        self.assertIn("brightening", claims["efficacy_domain"].value_json)  # pyright: ignore[reportArgumentType]

    def test_niacinamide_mapping(self):
        ingredient = parse_ingredient(NIACINAMIDE_RAW)
        claims = {c.key: c for c in map_ingredient(ingredient)}

        self.assertEqual(claims["comedogenic_risk"].value_text, "none")
        self.assertEqual(claims["irritation_potential"].value_text, "low")
        self.assertEqual(claims["evidence_strength"].value_text, "strong")
        self.assertEqual(
            sorted(claims["efficacy_domain"].value_json),  # pyright: ignore[reportArgumentType]
            ["anti_acne", "brightening"],
        )
        self.assertEqual(claims["functional_class"].value_json, ["humectant"])


class InciClientErrorTests(SimpleTestCase):
    def test_get_product_returns_none_for_structured_404(self):
        with mock.patch.object(
            inci_client,
            "_get",
            side_effect=HttpError("404 Not Found: /products/123", status_code=404),
        ):
            self.assertIsNone(inci_client.get_product("123"))

    def test_get_product_reraises_non_404_even_when_barcode_contains_404(self):
        with mock.patch.object(
            inci_client,
            "_get",
            side_effect=HttpError(
                "500 from /products/sku-404-oops",
                status_code=500,
            ),
        ):
            with self.assertRaises(HttpError):
                inci_client.get_product("sku-404-oops")

    def test_get_ingredient_reraises_unstructured_error_with_404_text(self):
        with mock.patch.object(
            inci_client,
            "_get",
            side_effect=HttpError("upstream error for 404-like ingredient"),
        ):
            with self.assertRaises(HttpError):
                inci_client.get_ingredient("404-like ingredient")


class InciIngestOrchestratorTests(TestCase):
    def setUp(self):
        upsert_property_definitions()
        self._retinol = parse_ingredient(RETINOL_RAW)

    def test_ingest_writes_compound_aliases_identifiers_and_properties(self):
        with mock.patch.object(
            inci_client, "get_ingredient", return_value=self._retinol
        ):
            result = ingest_inci_ingredient("Retinol")

        compound = Compound.objects.get(canonical_inci="RETINOL")
        self.assertEqual(result.compound_id, compound.pk)
        self.assertEqual(compound.primary_cas, "68-26-8")
        self.assertTrue(
            CompoundIdentifier.objects.filter(
                compound=compound, id_type="cas", id_value="68-26-8"
            ).exists()
        )
        self.assertTrue(
            CompoundIdentifier.objects.filter(
                compound=compound, id_type="ec", id_value="200-683-7"
            ).exists()
        )
        self.assertTrue(
            CompoundAlias.objects.filter(
                compound=compound, alias_text="Vitamin A", alias_type="inci"
            ).exists()
        )
        self.assertTrue(
            PropertyAssertion.objects.filter(
                compound=compound,
                property_def__key="functional_class",
                is_active=True,
                source_type=SourceType.AGGREGATOR,
            ).exists()
        )
        self.assertTrue(
            PropertyAssertion.objects.filter(
                compound=compound,
                property_def__key="inci_safety_score",
                value_numeric=6.5,
            ).exists()
        )
        profile = PropertyAssertion.objects.get(
            compound=compound, property_def__key="inci_profile"
        )
        self.assertEqual(profile.value_json["inciName"], "Retinol")
        self.assertGreater(result.properties_written, 0)

    def test_client_failure_degrades_gracefully(self):
        with mock.patch.object(
            inci_client, "get_ingredient", side_effect=RuntimeError("down")
        ):
            result = ingest_inci_ingredient("Retinol")

        self.assertTrue(Compound.objects.filter(canonical_inci="RETINOL").exists())
        self.assertTrue(result.errors)
        self.assertEqual(result.properties_written, 0)


class ProvenanceTests(TestCase):
    def setUp(self):
        upsert_property_definitions()
        self.compound = Compound.objects.create(
            canonical_inci="RETINOL",
            display_name="Retinol",
        )
        self.func_def = PropertyDefinition.objects.get(key="functional_class")
        self.source_ref = "inciapi:Retinol"

    def test_human_beats_aggregator_on_ingest(self):
        human = PropertyAssertion.objects.create(
            compound=self.compound,
            property_def=self.func_def,
            value_json=["active"],
            confidence=0.9,
            source_type=SourceType.HUMAN,
            source_ref="human:reviewer",
            is_active=True,
        )
        retinol = parse_ingredient(RETINOL_RAW)
        with mock.patch.object(inci_client, "get_ingredient", return_value=retinol):
            ingest_inci_ingredient("Retinol")

        human.refresh_from_db()
        inci = PropertyAssertion.objects.get(
            compound=self.compound,
            property_def=self.func_def,
            source_ref=self.source_ref,
        )
        self.assertTrue(human.is_active)
        self.assertFalse(inci.is_active)
        self.assertEqual(inci.superseded_by_id, human.pk)  # pyright: ignore[reportAttributeAccessIssue]

    def test_aggregator_beats_seed_on_ingest(self):
        seed = PropertyAssertion.objects.create(
            compound=self.compound,
            property_def=self.func_def,
            value_json=["excipient_base"],
            confidence=0.5,
            source_type=SourceType.SEED,
            source_ref="seed:reference",
            is_active=True,
        )
        retinol = parse_ingredient(RETINOL_RAW)
        with mock.patch.object(inci_client, "get_ingredient", return_value=retinol):
            ingest_inci_ingredient("Retinol")

        seed.refresh_from_db()
        inci = PropertyAssertion.objects.get(
            compound=self.compound,
            property_def=self.func_def,
            source_ref=self.source_ref,
        )
        self.assertFalse(seed.is_active)
        self.assertEqual(seed.superseded_by_id, inci.pk)  # pyright: ignore[reportAttributeAccessIssue]
        self.assertTrue(inci.is_active)

    def test_reingest_is_idempotent(self):
        retinol = parse_ingredient(RETINOL_RAW)
        with mock.patch.object(inci_client, "get_ingredient", return_value=retinol):
            ingest_inci_ingredient("Retinol")
            ingest_inci_ingredient("Retinol")

        active = PropertyAssertion.objects.filter(
            compound=self.compound,
            property_def=self.func_def,
            is_active=True,
        )
        self.assertEqual(active.count(), 1)
        inci_rows = PropertyAssertion.objects.filter(
            compound=self.compound,
            property_def=self.func_def,
            source_ref=self.source_ref,
        )
        self.assertEqual(inci_rows.count(), 1)

    def test_assert_property_updates_same_source_in_place(self):
        assert_property(
            self.compound,
            "functional_class",
            value_json=["humectant"],
            source_type=SourceType.AGGREGATOR,
            confidence=0.6,
            source_ref=self.source_ref,
            asserted_by="test",
        )
        assert_property(
            self.compound,
            "functional_class",
            value_json=["antioxidant", "emollient"],
            source_type=SourceType.AGGREGATOR,
            confidence=0.6,
            source_ref=self.source_ref,
            asserted_by="test",
        )
        rows = PropertyAssertion.objects.filter(
            compound=self.compound,
            property_def=self.func_def,
            source_ref=self.source_ref,
        )
        self.assertEqual(rows.count(), 1)
        self.assertEqual(
            rows.get().value_json,
            ["antioxidant", "emollient"],
        )
