"""Unit tests for data confidence scoring."""

from django.test import TestCase

from core.models import Brand, Compound, Formulation, FormulationIngredient, Product
from core.profiles.confidence import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, confidence_band, data_confidence


class ConfidenceComputationTests(TestCase):
    """Test data_confidence helper function."""

    def setUp(self):
        """Create test data."""
        self.brand = Brand.objects.create(name="TestBrand")
        self.product = Product.objects.create(name="TestProduct", brand=self.brand)
        self.water = Compound.objects.create(
            canonical_inci="WATER",
            display_name="Water",
        )
        self.glycerin = Compound.objects.create(
            canonical_inci="GLYCERIN",
            display_name="Glycerin",
        )

    def test_full_resolution(self):
        """All ingredients matched and resolved → 1.0 / high."""
        formulation = Formulation.objects.create(
            enrichment_status="complete",
            product=self.product,
            raw_inci_text="Water, Glycerin",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
            parse_status="matched",
            compound=self.water,
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=2,
            raw_text="Glycerin",
            parse_status="matched",
            compound=self.glycerin,
        )

        # Need to prefetch ingredients
        formulation = Formulation.objects.prefetch_related("ingredients").get(pk=formulation.id)
        conf = data_confidence(formulation)
        self.assertEqual(conf, 1.0)
        self.assertEqual(confidence_band(conf), "high")

    def test_partial_resolution(self):
        """3 of 10 ingredients resolved → 0.3 / low."""
        formulation = Formulation.objects.create(
            enrichment_status="complete",
            product=self.product,
            raw_inci_text="Water, Glycerin, Unknown, A, B, C, D, E, F, G",
        )
        # Create 3 resolved
        for i, compound in enumerate([self.water, self.glycerin, self.water]):
            FormulationIngredient.objects.create(
                formulation=formulation,
                position=i + 1,
                raw_text=f"Ingredient{i}",
                parse_status="matched",
                compound=compound,
            )
        # Create 7 unresolved
        for i in range(7):
            FormulationIngredient.objects.create(
                formulation=formulation,
                position=i + 4,
                raw_text=f"Unknown{i}",
                parse_status="unmatched",
            )

        formulation = Formulation.objects.prefetch_related("ingredients").get(pk=formulation.id)
        conf = data_confidence(formulation)
        self.assertAlmostEqual(conf, 0.3, places=1)
        self.assertEqual(confidence_band(conf), "low")

    def test_zero_ingredients(self):
        """No ingredients → 0.0."""
        formulation = Formulation.objects.create(
            enrichment_status="complete",
            product=self.product,
            raw_inci_text="",
        )

        formulation = Formulation.objects.prefetch_related("ingredients").get(pk=formulation.id)
        conf = data_confidence(formulation)
        self.assertEqual(conf, 0.0)
        self.assertEqual(confidence_band(conf), "low")

    def test_pending_enrichment_cap(self):
        """Pending enrichment caps confidence at 0.5."""
        formulation = Formulation.objects.create(
            product=self.product,
            raw_inci_text="Water, Glycerin",
            enrichment_status="pending",
        )
        # All resolved but enrichment pending
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
            parse_status="matched",
            compound=self.water,
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=2,
            raw_text="Glycerin",
            parse_status="matched",
            compound=self.glycerin,
        )

        formulation = Formulation.objects.prefetch_related("ingredients").get(pk=formulation.id)
        conf = data_confidence(formulation)
        self.assertEqual(conf, 0.5)
        self.assertEqual(confidence_band(conf), "medium")

    def test_matched_without_compound(self):
        """Matched status but no compound → unresolved."""
        formulation = Formulation.objects.create(
            enrichment_status="complete",
            product=self.product,
            raw_inci_text="Water, Unknown",
        )
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Water",
            parse_status="matched",
            compound=self.water,
        )
        # Matched but no compound
        FormulationIngredient.objects.create(
            formulation=formulation,
            position=2,
            raw_text="Unknown",
            parse_status="matched",
            compound=None,
        )

        formulation = Formulation.objects.prefetch_related("ingredients").get(pk=formulation.id)
        conf = data_confidence(formulation)
        self.assertEqual(conf, 0.5)
        self.assertEqual(confidence_band(conf), "medium")

    def test_confidence_band_boundaries(self):
        """Test band thresholds."""
        self.assertEqual(confidence_band(0.99), "high")
        self.assertEqual(confidence_band(0.8), "high")
        self.assertEqual(confidence_band(0.79), "medium")
        self.assertEqual(confidence_band(0.4), "medium")
        self.assertEqual(confidence_band(0.39), "low")
        self.assertEqual(confidence_band(0.0), "low")

    def test_confidence_constants(self):
        """Verify confidence constants match spec."""
        self.assertEqual(CONFIDENCE_HIGH, 0.8)
        self.assertEqual(CONFIDENCE_MEDIUM, 0.4)
