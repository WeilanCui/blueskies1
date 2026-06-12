from django.test import TestCase

from core.models import Compound, PropertyAssertion, PropertyDefinition
from core.models.properties import PropertyDomain, ValueType


class PropertyAssertionModelTests(TestCase):
    def test_string_uses_display_value_without_recursing(self):
        compound = Compound.objects.create(canonical_inci="AEROSOLS")
        property_def = PropertyDefinition.objects.create(
            key="usage-note",
            domain=PropertyDomain.COMPOUND,
            value_type=ValueType.TEXT,
            label="Usage note",
            description="Human readable usage note.",
        )
        assertion = PropertyAssertion.objects.create(
            compound=compound,
            property_def=property_def,
            value_text="pressurized format",
        )

        self.assertEqual(
            str(assertion),
            "usage-note=pressurized format on AEROSOLS",
        )
