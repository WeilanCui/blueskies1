from django.core.management.base import BaseCommand

from core.seeds.loader import seed_all


class Command(BaseCommand):
    help = (
        "Seed property ontology, glossary, interaction rules, and optional "
        "reference compounds. Idempotent — safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-reference-compounds",
            action="store_true",
            help="Only seed ontology metadata, not exemplar compounds.",
        )

    def handle(self, *args, **options):
        results = seed_all(
            include_reference_compounds=not options["skip_reference_compounds"]
        )

        self.stdout.write(self.style.SUCCESS("Ontology seed complete."))
        for section, counts in results.items():
            parts = ", ".join(f"{k}={v}" for k, v in counts.items())
            self.stdout.write(f"  {section}: {parts}")
