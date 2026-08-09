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
    source = serializers.CharField(read_only=True)
    concern = serializers.CharField(source="concern_slug", allow_null=True, read_only=True)
    position_factor = serializers.FloatField(allow_null=True, read_only=True)
    evidence_count = serializers.IntegerField(allow_null=True, read_only=True)
    evidence_multiplier = serializers.FloatField(allow_null=True, read_only=True)


class CoverageSummarySerializer(serializers.Serializer):
    """Read-only serializer for a CoverageSummary."""

    concern = serializers.CharField(source="concern_slug", read_only=True)
    concern_label = serializers.CharField(read_only=True)
    matched = serializers.IntegerField(read_only=True)
    total = serializers.IntegerField(read_only=True)
    matched_rules = serializers.ListField(
        child=serializers.CharField(), source="matched_labels", read_only=True
    )
    unmatched_rules = serializers.ListField(
        child=serializers.CharField(), source="unmatched_labels", read_only=True
    )


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
    coverage = serializers.SerializerMethodField()
    data_confidence = serializers.SerializerMethodField()
    confidence_band = serializers.CharField(read_only=True)

    def get_formulation_id(self, obj) -> int:
        return obj.formulation.id

    def get_product_name(self, obj) -> str:
        return obj.formulation.product.name or ""

    def get_brand_name(self, obj) -> str:
        if obj.formulation.product.brand is None:
            return ""
        return obj.formulation.product.brand.name or ""

    def get_warnings(self, obj):
        return RecommendationImpactSerializer(obj.warnings, many=True).data

    def get_penalties(self, obj):
        return RecommendationImpactSerializer(obj.penalties, many=True).data

    def get_boosts(self, obj):
        return RecommendationImpactSerializer(obj.boosts, many=True).data

    def get_coverage(self, obj):
        return CoverageSummarySerializer(obj.coverage, many=True).data

    def get_data_confidence(self, obj) -> float:
        return round(obj.data_confidence, 2)


class RecommendationScoreRequestSerializer(serializers.Serializer):
    """Request serializer for scoring a single formulation."""

    formulation_id = serializers.IntegerField(required=True)
