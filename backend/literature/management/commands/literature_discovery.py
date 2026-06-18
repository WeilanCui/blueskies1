from django.core.management.base import BaseCommand

from literature.discovery import (
    LiteratureDiscoveryRunner,
    candidate_compounds_for_literature,
    dispatch_pending_literature_discovery_events,
    enqueue_pending_compounds_for_literature,
)


class Command(BaseCommand):
    help = (
        "Run PubChem + PubMed ingestion for queued or pending formulation compounds."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=25,
            help="Max compounds to ingest this run (default 25).",
        )
        parser.add_argument(
            "--enqueue",
            type=int,
            metavar="N",
            help="First add up to N pending compounds to the discovery queue.",
        )
        parser.add_argument(
            "--enqueue-only",
            action="store_true",
            help="Only enqueue pending compounds; do not run ingestion.",
        )
        parser.add_argument(
            "--event-limit",
            type=int,
            default=100,
            help="Max pending discovery events to dispatch before ingestion.",
        )
        parser.add_argument(
            "--no-backfill",
            action="store_true",
            help="Only process explicit queue targets; skip pending-compound backfill.",
        )
        parser.add_argument(
            "--all-targets",
            action="store_true",
            help="Include non-formulation queue targets (e.g. legacy ingest_compound).",
        )
        parser.add_argument(
            "--include-non-formulation",
            action="store_true",
            help="Backfill compounds not linked to any product formulation.",
        )
        parser.add_argument("--max-articles", type=int, default=5)
        parser.add_argument("--max-related", type=int, default=3)
        parser.add_argument(
            "--enrich",
            action="store_true",
            help="Run LLM literature enrichment after ingest.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        formulation_only = not options["include_non_formulation"]

        if options["enqueue"]:
            enqueued = enqueue_pending_compounds_for_literature(
                options["enqueue"],
                formulation_only=formulation_only,
            )
            pending_total = candidate_compounds_for_literature(
                limit=1_000_000,
                formulation_only=formulation_only,
            ).count()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Enqueued {enqueued} compounds "
                    f"({pending_total} still pending without active queue row)."
                )
            )

        if options["enqueue_only"]:
            return

        event_result = dispatch_pending_literature_discovery_events(
            limit=options["event_limit"],
        )

        backfill_limit = 0 if options["no_backfill"] else None
        runner = LiteratureDiscoveryRunner(
            compound_limit=limit,
            backfill_limit=backfill_limit,
            max_articles=options["max_articles"],
            max_related=options["max_related"],
            enrich=options["enrich"],
            product_targets_only=not options["all_targets"],
            backfill_formulation_only=formulation_only,
        )
        result = runner.run()

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {result['compounds_processed']} compounds "
                f"({result['targets_processed']} from queue, "
                f"{result['backfill_processed']} backfill, "
                f"{result['stale_targets_requeued']} stale requeued, "
                f"{event_result['events_processed']} events dispatched)."
            )
        )
        for event in event_result["events"]:
            if event.get("error"):
                self.stdout.write(
                    self.style.WARNING(f"event:{event['event_id']}:{event['error']}")
                )
        for err in result["errors"]:
            self.stdout.write(self.style.WARNING(err))
