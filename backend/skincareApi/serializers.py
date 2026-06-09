from rest_framework import serializers


class SkincareProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    brand = serializers.CharField()
    name = serializers.CharField()
    ingredient_list = serializers.ListField(child=serializers.CharField())


class SkincareIngredientSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ingredient = serializers.CharField()


class SkincareProductCreateSerializer(serializers.Serializer):
    brand = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=255)
    ingredients = serializers.CharField(
        help_text='Comma-separated ingredient list, e.g. "water,glycerin,citric acid"'
    )
