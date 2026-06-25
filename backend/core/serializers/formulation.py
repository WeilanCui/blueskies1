from rest_framework import serializers

from core.models import Formulation, FormulationIngredient
from core.serializers.product import ProductSummarySerializer


class FormulationSubmitSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=512)
    brand = serializers.CharField(max_length=256, required=False, allow_blank=True, default="")
    formulation = serializers.CharField()


class FormulationIngredientSerializer(serializers.ModelSerializer):
    compound_name = serializers.SerializerMethodField()
    enrichment_status = serializers.SerializerMethodField()
    inherited_functional_classes = serializers.SerializerMethodField()
    effective_functional_classes = serializers.SerializerMethodField()
    is_function_override = serializers.SerializerMethodField()

    class Meta:
        model = FormulationIngredient
        fields = [
            "position",
            "raw_text",
            "parse_status",
            "compound",
            "compound_name",
            "enrichment_status",
            "inherited_functional_classes",
            "functional_classes_override",
            "effective_functional_classes",
            "is_function_override",
            "function_override_source",
            "function_override_confidence",
            "function_override_notes",
            "is_key_active",
            "active_note",
        ]

    def get_compound_name(self, obj: FormulationIngredient) -> str:
        if obj.compound is None:
            return ""
        return obj.compound.display_name or obj.compound.canonical_inci

    def get_enrichment_status(self, obj: FormulationIngredient) -> str:
        if obj.compound is None:
            return ""
        return obj.compound.enrichment_status

    def get_inherited_functional_classes(self, obj: FormulationIngredient) -> list[str]:
        return obj.inherited_functional_classes

    def get_effective_functional_classes(self, obj: FormulationIngredient) -> list[str]:
        return obj.effective_functional_classes

    def get_is_function_override(self, obj: FormulationIngredient) -> bool:
        return obj.is_function_override


class FormulationSerializer(serializers.ModelSerializer):
    product = ProductSummarySerializer(read_only=True)
    product_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    brand = serializers.CharField(read_only=True)
    ingredients = FormulationIngredientSerializer(many=True, read_only=True)
    ingredient_count = serializers.SerializerMethodField()

    class Meta:
        model = Formulation
        fields = [
            "id",
            "product_id",
            "product",
            "name",
            "brand",
            "sku",
            "barcode",
            "market",
            "made_in",
            "version_label",
            "effective_from",
            "effective_to",
            "enrichment_status",
            "raw_inci_text",
            "ingredient_count",
            "ingredients",
            "created_at",
        ]

    def get_ingredient_count(self, obj: Formulation) -> int:
        return obj.ingredients.count()
