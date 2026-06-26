from rest_framework import serializers

from core.models import (
    ChemicalClass,
    ChemicalClassMembership,
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


class ChemicalClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChemicalClass
        fields = ["id", "name", "slug", "description", "parent"]


class ChemicalClassMembershipSerializer(serializers.ModelSerializer):
    chemical_class = ChemicalClassSerializer(read_only=True)

    class Meta:
        model = ChemicalClassMembership
        fields = [
            "chemical_class",
            "is_primary",
            "is_active",
            "confidence",
            "source_type",
            "source_ref",
            "rationale",
        ]


class PropertyAssertionSerializer(serializers.ModelSerializer):
    key = serializers.CharField(source="property_def.key", read_only=True)
    label = serializers.CharField(source="property_def.label", read_only=True)
    value = serializers.SerializerMethodField()
    inherited_from = serializers.SerializerMethodField()

    class Meta:
        model = PropertyAssertion
        fields = [
            "key",
            "label",
            "value",
            "inherited_from",
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

    def get_inherited_from(self, obj: PropertyAssertion) -> str:
        if obj.chemical_class_id is None:
            return ""
        return obj.chemical_class.name


class CompoundSerializer(serializers.ModelSerializer):
    structure = CompoundStructureSerializer(read_only=True)
    aliases = CompoundAliasSerializer(many=True, read_only=True)
    identifiers = CompoundIdentifierSerializer(many=True, read_only=True)
    chemical_classes = serializers.SerializerMethodField()
    properties = serializers.SerializerMethodField()
    inherited_properties = serializers.SerializerMethodField()
    effective_properties = serializers.SerializerMethodField()
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
            "chemical_classes",
            "properties",
            "inherited_properties",
            "effective_properties",
            "literature_count",
        ]

    def get_chemical_classes(self, obj: Compound) -> list:
        memberships = [
            membership
            for membership in obj.chemical_class_memberships.all()
            if membership.is_active
        ]
        return ChemicalClassMembershipSerializer(memberships, many=True).data

    def get_properties(self, obj: Compound) -> list:
        active = [a for a in obj.property_assertions.all() if a.is_active]
        return PropertyAssertionSerializer(active, many=True).data

    def get_inherited_properties(self, obj: Compound) -> list:
        return PropertyAssertionSerializer(
            obj.inherited_property_assertions(),
            many=True,
        ).data

    def get_effective_properties(self, obj: Compound) -> list:
        return PropertyAssertionSerializer(
            obj.effective_property_assertions(),
            many=True,
        ).data

    def get_literature_count(self, obj: Compound) -> int:
        count = getattr(obj, "literature_count", None)
        if count is not None:
            return count
        return obj.literature_links.count()
