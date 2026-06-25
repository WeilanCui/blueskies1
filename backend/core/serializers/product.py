from rest_framework import serializers

from core.models.product import Product


class ProductSummarySerializer(serializers.ModelSerializer):
    brand = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "brand",
            "name",
            "display_name",
            "category",
            "image_url",
        ]

    def get_brand(self, obj: Product) -> str:
        if obj.brand_id is None:
            return ""
        return obj.brand.name
