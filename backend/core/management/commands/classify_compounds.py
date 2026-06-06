from django.core.management.base import BaseCommand

from core.enrichment.compound_bootstrap import apply_entity_classification
from core.models import Compound


class Command(BaseCommand):
    help = "Classify compound entity types from INCI patterns and write property assertions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Re-apply classification even when entity_type is already set.",
        )
        parser.add_argument(
            "--unknown-only",
            action="store_true",
            help="Only classify compounds with entity_type=unknown.",
        )
        parser.add_argument(
            "--inci",
            type=str,
            help="Classify a single INCI name (creates compound if missing).",
        )

    def handle(self, *args, **options):
        overwrite = options["overwrite"]
        unknown_only = options["unknown_only"]
        inci = options.get("inci")

        if inci:
            canonical = inci.upper().strip()
            compound, _ = Compound.objects.get_or_create(
                canonical_inci=canonical,
                defaults={"display_name": canonical.title()},
            )
            result = apply_entity_classification(
                compound, overwrite=overwrite, asserted_by="classify_compounds"
            )
            self.stdout.write(
                f"{canonical}: {result.entity_type} "
                f"(structure_resolvable={result.structure_resolvable}, "
                f"confidence={result.confidence})"
            )
            return

        queryset = Compound.objects.all()
        if unknown_only:
            queryset = queryset.filter(entity_type="unknown")

        count = 0
        for compound in queryset.iterator():
            result = apply_entity_classification(
                compound, overwrite=overwrite, asserted_by="classify_compounds"
            )
            count += 1
            self.stdout.write(
                f"{compound.canonical_inci}: {result.entity_type} "
                f"({result.confidence:.2f})"
            )

        self.stdout.write(self.style.SUCCESS(f"Classified {count} compound(s)."))
