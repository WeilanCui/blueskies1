from django.test import SimpleTestCase

from core.enrichment.entity_classifier import classify_inci


class EntityClassifierTests(SimpleTestCase):
    def test_parfum_is_fragrance_blend(self):
        result = classify_inci("PARFUM")
        self.assertEqual(result.entity_type, "fragrance_blend")
        self.assertFalse(result.structure_resolvable)
        self.assertIn("fragrance", result.suggested_functional_classes)

    def test_botanical_extract(self):
        result = classify_inci("ALOE BARBADENSIS LEAF JUICE")
        self.assertEqual(result.entity_type, "botanical_extract")
        self.assertFalse(result.structure_resolvable)

    def test_uvcb_petrolatum(self):
        result = classify_inci("PETROLATUM")
        self.assertEqual(result.entity_type, "uvcb")

    def test_silicone(self):
        result = classify_inci("DIMETHICONE")
        self.assertEqual(result.entity_type, "silicone")

    def test_polymer(self):
        result = classify_inci("CARBOMER")
        self.assertEqual(result.entity_type, "polymer")

    def test_small_molecule_heuristic(self):
        result = classify_inci("NIACINAMIDE")
        self.assertEqual(result.entity_type, "small_molecule")
        self.assertTrue(result.structure_resolvable)
