from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import (
    ChemicalClass,
    ChemicalClassMembership,
    Compound,
    PropertyAssertion,
    PropertyDefinition,
    SourceType,
)
from literature.seeds.loader import upsert_chemical_classes, upsert_property_definitions


class ChemicalClassInheritanceTests(TestCase):
    def setUp(self):
        upsert_property_definitions()
        self.retinoids = ChemicalClass.objects.create(
            name="Retinoids",
            slug="retinoids",
        )
        self.retinal = Compound.objects.create(
            canonical_inci="RETINAL",
            display_name="Retinal",
        )
        ChemicalClassMembership.objects.create(
            compound=self.retinal,
            chemical_class=self.retinoids,
            is_primary=True,
            source_type=SourceType.SEED,
        )
        self.light_sensitive = PropertyDefinition.objects.get(key="light_sensitive")
        self.irritation = PropertyDefinition.objects.get(key="irritation_potential")

    def test_compound_inherits_active_class_property(self):
        PropertyAssertion.objects.create(
            chemical_class=self.retinoids,
            property_def=self.light_sensitive,
            value_bool=True,
            source_type=SourceType.SEED,
            is_active=True,
        )

        inherited = list(self.retinal.inherited_property_assertions())

        self.assertEqual(len(inherited), 1)
        self.assertEqual(inherited[0].chemical_class, self.retinoids)
        self.assertTrue(inherited[0].value_bool)

    def test_direct_compound_property_overrides_class_property(self):
        PropertyAssertion.objects.create(
            chemical_class=self.retinoids,
            property_def=self.irritation,
            value_text="moderate",
            source_type=SourceType.SEED,
            is_active=True,
        )
        direct = PropertyAssertion.objects.create(
            compound=self.retinal,
            property_def=self.irritation,
            value_text="low",
            source_type=SourceType.HUMAN,
            is_active=True,
        )

        effective = self.retinal.effective_property_assertions()

        self.assertIn(direct, effective)
        self.assertFalse(
            any(assertion.chemical_class_id for assertion in effective),
        )

    def test_property_assertion_allows_exactly_one_target(self):
        assertion = PropertyAssertion(
            compound=self.retinal,
            chemical_class=self.retinoids,
            property_def=self.light_sensitive,
            value_bool=True,
        )

        with self.assertRaises(ValidationError):
            assertion.clean()


class ChemicalClassSeedTests(TestCase):
    def setUp(self):
        upsert_property_definitions()

    def test_seed_creates_retinoid_class_memberships_and_properties(self):
        result = upsert_chemical_classes()

        retinoids = ChemicalClass.objects.get(slug="retinoids")
        self.assertGreaterEqual(result["memberships_written"], 3)
        self.assertTrue(
            ChemicalClassMembership.objects.filter(
                chemical_class=retinoids,
                compound__canonical_inci="RETINOL",
                is_active=True,
            ).exists()
        )
        self.assertTrue(
            PropertyAssertion.objects.filter(
                chemical_class=retinoids,
                property_def__key="light_sensitive",
                value_bool=True,
                is_active=True,
            ).exists()
        )
