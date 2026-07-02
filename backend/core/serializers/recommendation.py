from rest_framework import serializers


class RecommendationImpactSerializer(serializers.Serializer):
    """Read-only serializer for a ConstraintImpact."""

    constraint_id = serializers.IntegerField(read_only=True)
    kind = serializers.CharField(read_only=True)
    enforcement = serializers.CharField(read_only=True)
    severity = serializers.CharField(read_only=True)
    target_type = serializers.CharField(read_only=True)
    target = serializers.CharField(read_only=True)
    reason = serializers.CharField(read_only=True)
    score_delta = serializers.IntegerField(read_only=True)


class RecommendationMatchSerializer(serializers.Serializer):
    """Read-only serializer for a RecommendationMatch."""

    formulation_id = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    brand_name = serializers.SerializerMethodField()
    final_score = serializers.IntegerField(read_only=True)
    excluded = serializers.BooleanField(read_only=True)
    reasons = serializers.ListField(child=serializers.CharField(), read_only=True)
    warnings = serializers.SerializerMethodField()
    penalties = serializers.SerializerMethodField()
    boosts = serializers.SerializerMethodField()

    def get_formulation_id(self, obj) -> int:
        return obj.formulation.id

    def get_product_name(self, obj) -> str:
        if obj.formulation.product is None:
            return ""
        return obj.formulation.product.name or ""

    def get_brand_name(self, obj) -> str:
        if obj.formulation.product is None or obj.formulation.product.brand is None:
            return ""
        return obj.formulation.product.brand.name or ""

    def get_warnings(self, obj):
        return RecommendationImpactSerializer(obj.warnings, many=True).data

    def get_penalties(self, obj):
        return RecommendationImpactSerializer(obj.penalties, many=True).data

    def get_boosts(self, obj):
        return RecommendationImpactSerializer(obj.boosts, many=True).data


class RecommendationScoreRequestSerializer(serializers.Serializer):
    """Request serializer for scoring a single formulation."""

    formulation_id = serializers.IntegerField(required=True)
