from rest_framework import serializers

from core.models import (
    Compound,
    CompoundAlias,
    CompoundIdentifier,
    CompoundStructure,
    PropertyAssertion,
)


class CompoundAliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompoundAlias
        fields = ["alias_text", "alias_type", "source"]


class CompoundIdentifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompoundIdentifier
        fields = ["id_type", "id_value", "source", "is_primary"]


class CompoundStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompoundStructure
        fields = [
            "smiles",
            "inchi",
            "inchikey",
            "molecular_formula",
            "molecular_weight",
            "match_quality",
            "source",
        ]


class PropertyAssertionSerializer(serializers.ModelSerializer):
    key = serializers.CharField(source="property_def.key", read_only=True)
    label = serializers.CharField(source="property_def.label", read_only=True)
    value = serializers.SerializerMethodField()

    class Meta:
        model = PropertyAssertion
        fields = [
            "key",
            "label",
            "value",
            "source_type",
            "source_name",
            "source_ref",
            "source_url",
            "confidence",
            "evidence_summary",
            "asserted_by",
            "retrieved_at",
        ]

    def get_value(self, obj: PropertyAssertion) -> str:
        return obj.display_value()


class CompoundSerializer(serializers.ModelSerializer):
    structure = CompoundStructureSerializer(read_only=True)
    aliases = CompoundAliasSerializer(many=True, read_only=True)
    identifiers = CompoundIdentifierSerializer(many=True, read_only=True)
    properties = serializers.SerializerMethodField()
    literature_count = serializers.SerializerMethodField()

    class Meta:
        model = Compound
        fields = [
            "id",
            "canonical_inci",
            "display_name",
            "entity_type",
            "primary_cas",
            "structure_resolvable",
            "enrichment_status",
            "notes",
            "structure",
            "aliases",
            "identifiers",
            "properties",
            "literature_count",
        ]

    def get_properties(self, obj: Compound) -> list:
        active = [a for a in obj.property_assertions.all() if a.is_active]
        return PropertyAssertionSerializer(active, many=True).data

    def get_literature_count(self, obj: Compound) -> int:
        return len(obj.literature_links.all())
