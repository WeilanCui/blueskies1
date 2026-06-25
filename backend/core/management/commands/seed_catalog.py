from django.core.management.base import BaseCommand

from core.seeds.csv_catalog import DEFAULT_SEED_DIR, discover_csv_files
from core.seeds.loader import seed_catalog


class Command(BaseCommand):
    help = (
        "Seed brands, products, formulations, and ingredient rows from the "
        "reference catalog and/or data/*.csv files. Idempotent — safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reference-only",
            action="store_true",
            help="Only load the small hardcoded reference catalog (scan page demo data).",
        )
        parser.add_argument(
            "--csv-only",
            action="store_true",
            help="Only load product rows from CSV files in the data/ folder.",
        )
        parser.add_argument(
            "--seed-dir",
            default=None,
            help=f"Directory containing catalog CSV files (default: {DEFAULT_SEED_DIR}).",
        )

    def handle(self, *args, **options):
        if options["reference_only"] and options["csv_only"]:
            self.stderr.write(
                self.style.ERROR("Choose at most one of --reference-only and --csv-only.")
            )
            return

        include_reference = not options["csv_only"]
        include_csv = not options["reference_only"]
        seed_dir = options["seed_dir"] or str(DEFAULT_SEED_DIR)

        if include_csv:
            csv_files = discover_csv_files(seed_dir)
            if not csv_files:
                self.stderr.write(
                    self.style.WARNING(f"No CSV files found in {seed_dir}")
                )
            else:
                names = ", ".join(path.name for path in csv_files)
                self.stdout.write(f"CSV files: {names}")

        results = seed_catalog(
            include_reference=include_reference,
            include_csv=include_csv,
            seed_dir=seed_dir,
        )

        self.stdout.write(self.style.SUCCESS("Catalog seed complete."))
        for section, counts in results.items():
            parts = ", ".join(f"{key}={value}" for key, value in counts.items())
            self.stdout.write(f"  {section}: {parts}")
