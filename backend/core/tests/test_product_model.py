from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Formulation, FormulationIngredient, Product


class ProductModelTests(TestCase):
    def test_product_can_have_multiple_formulation_variants(self):
        product = Product.objects.create(
            brand="Blueskies",
            name="Barrier Cream",
        )
        first = Formulation.objects.create(
            product=product,
            barcode="111111111111",
            market="US",
            made_in="United States",
            raw_inci_text="Water, Glycerin",
        )
        second = Formulation.objects.create(
            product=product,
            barcode="222222222222",
            market="EU",
            made_in="France",
            raw_inci_text="Aqua, Glycerin",
        )

        self.assertEqual(product.formulations.count(), 2)
        self.assertEqual(first.name, "Barrier Cream")
        self.assertEqual(second.brand, "Blueskies")

    def test_product_brand_name_identity_is_case_insensitive(self):
        Product.objects.create(brand="Blueskies", name="Barrier Cream")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.create(brand="blueskies", name="barrier cream")

    def test_formulation_ingredient_can_mark_key_active(self):
        product = Product.objects.create(
            brand="Blueskies",
            name="Brightening Serum",
        )
        formulation = Formulation.objects.create(product=product)
        ingredient = FormulationIngredient.objects.create(
            formulation=formulation,
            position=1,
            raw_text="Niacinamide",
            is_key_active=True,
            active_note="Hero brightening active",
        )

        self.assertTrue(ingredient.is_key_active)
        self.assertEqual(ingredient.active_note, "Hero brightening active")
