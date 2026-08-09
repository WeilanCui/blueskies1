"""Bounded search endpoints backing the skincare catalog page.

The catalog list endpoints return every row, which is fine for the small
server-rendered slices they were written for but not for a browsable search
over ~1.6k products and ~5.9k compounds. These endpoints page the result set
and report the full match count alongside it.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Compound, CompoundAlias, Formulation, FormulationIngredient
from core.models.brand import Brand
from core.models.product import Product


def make_product(brand_name: str, name: str, inci: str = "Water", **kwargs) -> Product:
    brand, _ = Brand.objects.get_or_create(name=brand_name)
    product = Product.objects.create(brand=brand, name=name, **kwargs)
    formulation = Formulation.objects.create(product=product, raw_inci_text=inci)
    for position, raw in enumerate(part.strip() for part in inci.split(",")):
        FormulationIngredient.objects.create(
            formulation=formulation, position=position, raw_text=raw
        )
    return product


class ProductSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("product-catalog-search")

    def test_envelope_reports_query_paging_and_total_count(self):
        for index in range(5):
            make_product("Blueskies", f"Barrier Cream {index}")

        response = self.client.get(self.url, {"limit": 2, "page": 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["query"], "")
        self.assertEqual(response.data["limit"], 2)
        self.assertEqual(response.data["page"], 1)
        # count is the size of the whole match set, not of this page.
        self.assertEqual(response.data["count"], 5)
        self.assertEqual(len(response.data["results"]), 2)

    def test_second_page_returns_the_next_slice(self):
        for index in range(5):
            make_product("Blueskies", f"Barrier Cream {index}")

        first = self.client.get(self.url, {"limit": 2, "page": 1})
        second = self.client.get(self.url, {"limit": 2, "page": 2})

        first_ids = [row["product_id"] for row in first.data["results"]]
        second_ids = [row["product_id"] for row in second.data["results"]]
        self.assertEqual(len(second_ids), 2)
        self.assertFalse(set(first_ids) & set(second_ids))

    def test_query_matches_name_and_brand(self):
        make_product("Blueskies", "Barrier Cream")
        make_product("Other Labs", "Niacinamide Serum")

        by_name = self.client.get(self.url, {"q": "barrier"})
        by_brand = self.client.get(self.url, {"q": "other labs"})

        self.assertEqual(by_name.data["count"], 1)
        self.assertEqual(by_name.data["results"][0]["name"], "Barrier Cream")
        self.assertEqual(by_brand.data["count"], 1)
        self.assertEqual(by_brand.data["results"][0]["name"], "Niacinamide Serum")

    def test_results_use_the_catalog_serializer_shape(self):
        make_product("Blueskies", "Barrier Cream", inci="Water, Glycerin")

        response = self.client.get(self.url, {"q": "barrier"})

        row = response.data["results"][0]
        self.assertEqual(row["brand"], "Blueskies")
        self.assertEqual(row["ingredient_count"], 2)
        self.assertEqual(
            [item["name"] for item in row["ingredients"]], ["Water", "Glycerin"]
        )
        # position is what the UI keys ingredient rows on.
        self.assertEqual([item["position"] for item in row["ingredients"]], [0, 1])

    def test_products_without_a_formulation_are_excluded(self):
        Product.objects.create(brand=Brand.objects.create(name="Ghost"), name="No Formula")

        response = self.client.get(self.url)

        self.assertEqual(response.data["count"], 0)

    def test_limit_is_clamped_and_bad_paging_falls_back_to_defaults(self):
        for index in range(3):
            make_product("Blueskies", f"Cream {index}")

        response = self.client.get(self.url, {"limit": "banana", "page": "-4"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["page"], 1)
        self.assertEqual(response.data["count"], 3)

    def test_limit_cannot_exceed_the_hard_ceiling(self):
        response = self.client.get(self.url, {"limit": 10_000})

        self.assertLessEqual(response.data["limit"], 100)


class CompoundSearchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("compound-search")

    def test_matches_canonical_inci_display_name_and_alias(self):
        Compound.objects.create(canonical_inci="NIACINAMIDE", display_name="Niacinamide")
        hyaluronic = Compound.objects.create(
            canonical_inci="SODIUM HYALURONATE", display_name="Sodium Hyaluronate"
        )
        CompoundAlias.objects.create(
            compound=hyaluronic, alias_text="Hyaluronic Acid", alias_type="common"
        )

        by_inci = self.client.get(self.url, {"q": "NIACIN"})
        by_display = self.client.get(self.url, {"q": "sodium hyal"})
        by_alias = self.client.get(self.url, {"q": "hyaluronic acid"})

        self.assertEqual(by_inci.data["count"], 1)
        self.assertEqual(by_display.data["count"], 1)
        self.assertEqual(by_alias.data["count"], 1)
        self.assertEqual(by_alias.data["results"][0]["ingredient"], "Sodium Hyaluronate")

    def test_alias_match_does_not_duplicate_the_compound(self):
        compound = Compound.objects.create(
            canonical_inci="GLYCERIN", display_name="Glycerin"
        )
        CompoundAlias.objects.create(
            compound=compound, alias_text="Glycerine", alias_type="common"
        )
        CompoundAlias.objects.create(
            compound=compound, alias_text="Glycerol", alias_type="common"
        )

        response = self.client.get(self.url, {"q": "glycer"})

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_results_are_light_id_and_ingredient_rows(self):
        compound = Compound.objects.create(
            canonical_inci="NIACINAMIDE", display_name="Niacinamide"
        )

        response = self.client.get(self.url, {"q": "niacinamide"})

        self.assertEqual(
            response.data["results"][0], {"id": compound.id, "ingredient": "Niacinamide"}
        )

    def test_falls_back_to_canonical_inci_when_display_name_is_blank(self):
        Compound.objects.create(canonical_inci="TOCOPHEROL", display_name="")

        response = self.client.get(self.url, {"q": "tocopherol"})

        self.assertEqual(response.data["results"][0]["ingredient"], "TOCOPHEROL")

    def test_paging_reports_total_count(self):
        for index in range(5):
            Compound.objects.create(canonical_inci=f"COMPOUND {index}")

        response = self.client.get(self.url, {"q": "compound", "limit": 2, "page": 2})

        self.assertEqual(response.data["count"], 5)
        self.assertEqual(len(response.data["results"]), 2)
