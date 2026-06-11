from django.core.management.base import BaseCommand

from literature.ingestion import inci_client, ingest_inci_ingredient


class Command(BaseCommand):
    help = "Ingest cosmetic ingredient data from the INCI API (inciapi.com)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--q",
            dest="query",
            help="Search query; ingest each matching ingredient.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Max search results to ingest (with --q).",
        )
        parser.add_argument(
            "--inci",
            action="append",
            dest="inci",
            help="INCI name to ingest directly (repeatable).",
        )

    def handle(self, *args, **options):
        names: list[str] = []

        if options.get("query"):
            try:
                results = inci_client.search_ingredients(
                    options["query"],
                    limit=options["limit"],
                )
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(self.style.ERROR(f"Search failed: {exc}"))
                return
            if not results:
                self.stdout.write(self.style.WARNING("No ingredients found."))
                return
            self.stdout.write(
                f"Found {len(results)} ingredient(s): "
                + ", ".join(r.inci_name for r in results)
            )
            names.extend(r.inci_name for r in results)

        if options.get("inci"):
            names.extend(options["inci"])

        if not names:
            self.stderr.write(
                self.style.ERROR("Provide --q <query> and/or --inci <name>.")
            )
            return

        for name in names:
            result = ingest_inci_ingredient(name)
            style = self.style.SUCCESS if not result.errors else self.style.WARNING
            self.stdout.write(style(result.summary()))
            for err in result.errors:
                self.stdout.write(self.style.WARNING(f"  ! {err}"))
