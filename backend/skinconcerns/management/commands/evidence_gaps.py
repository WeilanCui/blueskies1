from collections import defaultdict

from django.core.management.base import BaseCommand

from skinconcerns.models import ConcernRule, ConcernEvidence


class Command(BaseCommand):
    help = "List active concern rules with zero rule-scoped active evidence."

    def handle(self, *args, **options):
        # Get all active rules
        active_rules = ConcernRule.objects.filter(is_active=True).select_related("concern")

        # Find rules with zero rule-scoped active evidence
        gaps = defaultdict(list)
        for rule in active_rules:
            # Check if rule has any rule-scoped active evidence
            evidence_count = ConcernEvidence.objects.filter(
                rule_id=rule.id,
                is_active=True,
            ).count()

            if evidence_count == 0:
                gaps[rule.concern.slug].append((rule.key, rule.rule_kind))

        # Output: grouped by concern slug
        if gaps:
            for concern_slug in sorted(gaps.keys()):
                for rule_key, rule_kind in gaps[concern_slug]:
                    self.stdout.write(f"{concern_slug}  {rule_key}  {rule_kind}")
        else:
            self.stdout.write(self.style.SUCCESS("No rules with zero evidence found."))
