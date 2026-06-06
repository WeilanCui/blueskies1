from django.core.management.base import BaseCommand

from core.ingestion import ingest_compound

DEFAULT_SAMPLE = [
    "1,2-Hexanediol",
    "Niacinamide",
    "Glycerin",
    "Phenoxyethanol",
]


class Command(BaseCommand):
    help = "Ingest compound structure (PubChem) and UX-relevant literature (PubMed)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--inci",
            action="append",
            dest="inci",
            help="Compound/INCI name to ingest (repeatable). Defaults to a sample list.",
        )
        parser.add_argument(
            "--max-degree",
            type=int,
            choices=[1, 2],
            default=1,
            help="Relationship expansion depth (1 = direct, 2 = co-mentioned compounds).",
        )
        parser.add_argument("--max-articles", type=int, default=10)
        parser.add_argument("--max-related", type=int, default=5)
        parser.add_argument(
            "--no-pubmed",
            action="store_true",
            help="Resolve structure from PubChem only; skip PubMed literature.",
        )

    def handle(self, *args, **options):
        names = options.get("inci") or DEFAULT_SAMPLE
        for name in names:
            result = ingest_compound(
                name,
                max_degree=options["max_degree"],
                max_articles=options["max_articles"],
                max_related=options["max_related"],
                with_pubmed=not options["no_pubmed"],
            )
            style = self.style.SUCCESS if not result.errors else self.style.WARNING
            self.stdout.write(style(result.summary()))
            if result.related_compounds:
                self.stdout.write(
                    "  related: " + ", ".join(result.related_compounds)
                )
            for err in result.errors:
                self.stdout.write(self.style.WARNING(f"  ! {err}"))
