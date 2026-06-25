from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from core.admin import FormulationAdmin
from core.models import (
    Compound,
    Formulation,
    FormulationIngredient,
    PropertyAssertion,
    PropertyDefinition,
    SourceType,
)
from core.models.brand import Brand
from core.models.product import Product
from core.models.properties import PropertyDomain, ValueType
from core.serializers import FormulationIngredientSerializer


class FormulationIngredientFunctionTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Blueskies")
        self.product = Product.objects.create(brand=self.brand, name="Barrier Cream")
        self.formulation = Formulation.objects.create(product=self.product)
        self.functional_class = PropertyDefinition.objects.create(
            key="functional_class",
            domain=PropertyDomain.COMPOUND,
            value_type=ValueType.LIST,
            label="Functional class",
            description="Ingredient role in formulation.",
        )

    def create_compound(self, classes):
        compound = Compound.objects.create(canonical_inci="GLYCERIN")
        PropertyAssertion.objects.create(
            compound=compound,
            property_def=self.functional_class,
            value_json=classes,
            is_active=True,
        )
        return compound

    def test_inherits_compound_functional_classes_when_no_override_exists(self):
        compound = self.create_compound(["humectant", "solvent"])
        ingredient = FormulationIngredient.objects.create(
            formulation=self.formulation,
            position=1,
            raw_text="Glycerin",
            compound=compound,
        )

        self.assertEqual(ingredient.inherited_functional_classes, ["humectant", "solvent"])
        self.assertEqual(ingredient.effective_functional_classes, ["humectant", "solvent"])
        self.assertFalse(ingredient.is_function_override)

    def test_override_replaces_inherited_compound_functional_classes(self):
        compound = self.create_compound(["humectant", "solvent"])
        ingredient = FormulationIngredient.objects.create(
            formulation=self.formulation,
            position=1,
            raw_text="Glycerin",
            compound=compound,
            functional_classes_override=["solvent"],
            function_override_source=SourceType.HUMAN,
            function_override_confidence=0.95,
            function_override_notes="Used primarily as a solvent in this formula.",
        )

        self.assertEqual(ingredient.inherited_functional_classes, ["humectant", "solvent"])
        self.assertEqual(ingredient.effective_functional_classes, ["solvent"])
        self.assertTrue(ingredient.is_function_override)

    def test_ingredient_with_no_compound_and_no_override_returns_empty_classes(self):
        ingredient = FormulationIngredient.objects.create(
            formulation=self.formulation,
            position=1,
            raw_text="Unknown extract",
        )

        self.assertEqual(ingredient.inherited_functional_classes, [])
        self.assertEqual(ingredient.effective_functional_classes, [])
        self.assertFalse(ingredient.is_function_override)

    def test_is_key_active_is_independent_from_function_override(self):
        compound = self.create_compound(["humectant"])
        ingredient = FormulationIngredient.objects.create(
            formulation=self.formulation,
            position=1,
            raw_text="Glycerin",
            compound=compound,
            is_key_active=True,
            active_note="Hero hydration claim.",
        )

        self.assertTrue(ingredient.is_key_active)
        self.assertFalse(ingredient.is_function_override)
        self.assertEqual(ingredient.effective_functional_classes, ["humectant"])

    def test_serializer_exposes_inherited_override_effective_and_flag(self):
        compound = self.create_compound(["humectant", "solvent"])
        ingredient = FormulationIngredient.objects.create(
            formulation=self.formulation,
            position=1,
            raw_text="Glycerin",
            compound=compound,
            functional_classes_override=["humectant"],
            function_override_source=SourceType.HUMAN,
            function_override_confidence=0.8,
            function_override_notes="Primary role in this moisturizer.",
        )

        data = FormulationIngredientSerializer(ingredient).data

        self.assertEqual(data["inherited_functional_classes"], ["humectant", "solvent"])
        self.assertEqual(data["functional_classes_override"], ["humectant"])
        self.assertEqual(data["effective_functional_classes"], ["humectant"])
        self.assertTrue(data["is_function_override"])
        self.assertEqual(data["function_override_source"], SourceType.HUMAN)
        self.assertEqual(data["function_override_confidence"], 0.8)
        self.assertEqual(
            data["function_override_notes"],
            "Primary role in this moisturizer.",
        )

    def test_formulation_admin_inline_loads_function_fields(self):
        compound = self.create_compound(["humectant"])
        FormulationIngredient.objects.create(
            formulation=self.formulation,
            position=1,
            raw_text="Glycerin",
            compound=compound,
            functional_classes_override=["solvent"],
        )
        request = RequestFactory().get("/admin/core/formulation/1/change/")
        User = get_user_model()
        request.user = User(is_staff=True, is_superuser=True)
        model_admin = FormulationAdmin(Formulation, AdminSite())

        formsets, inline_instances = model_admin._create_formsets(  # pyright: ignore[reportAttributeAccessIssue]
            request,
            self.formulation,
            change=True,
        )

        self.assertEqual(len(formsets), 1)
        self.assertEqual(inline_instances[0].__class__.__name__, "FormulationIngredientInline")
        self.assertEqual(formsets[0].total_form_count(), 1)
