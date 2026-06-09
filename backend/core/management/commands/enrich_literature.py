from django.core.management.base import BaseCommand

from core.enrichment import enrich_compound_literature, get_extractor
from core.models import Compound, CompoundLiterature, LiteratureEnrichmentStatus


class Command(BaseCommand):
    help = "Enrich compound-literature links with LLM extraction over stored abstracts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--inci",
            action="append",
            dest="inci",
            help="Compound INCI name (repeatable). Defaults to all compounds with pending links.",
        )
        parser.add_argument("--pmid", help="Restrict enrichment to a single PubMed id.")
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum links to enrich per compound.",
        )
        parser.add_argument(
            "--reenrich",
            action="store_true",
            help="Re-run enrichment even when status is already enriched.",
        )
        parser.add_argument(
            "--extractor",
            choices=["auto", "stub", "openai"],
            default="auto",
            help="Extractor backend (auto uses OpenAI when OPENAI_API_KEY is set).",
        )

    def handle(self, *args, **options):
        extractor = get_extractor(options["extractor"])
        inci_names = options.get("inci")

        if inci_names:
            compounds = [
                Compound.objects.get(canonical_inci=name.upper()) for name in inci_names
            ]
        else:
            compound_ids = (
                CompoundLiterature.objects.filter(
                    enrichment_status=LiteratureEnrichmentStatus.PENDING
                )
                .values_list("compound_id", flat=True)
                .distinct()
            )
            compounds = list(Compound.objects.filter(pk__in=compound_ids))

        if not compounds:
            self.stdout.write(self.style.WARNING("No compound-literature links to enrich."))
            return

        total = 0
        for compound in compounds:
            results = enrich_compound_literature(
                compound,
                reenrich=options["reenrich"],
                extractor=extractor,
                limit=options["limit"],
                pmid=options.get("pmid"),
            )
            enriched = sum(1 for item in results if item is not None)
            total += enriched
            self.stdout.write(
                self.style.SUCCESS(
                    f"{compound.canonical_inci}: enriched {enriched}/{len(results)} "
                    f"via {extractor.name}"
                )
            )

        self.stdout.write(self.style.SUCCESS(f"Done. {total} link(s) enriched."))
