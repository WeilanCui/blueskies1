"""Tests for evidence_gaps management command."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from literature.models import LiteratureReference
from skinconcerns.models import (
    ConcernRule,
    ConcernEvidence,
    RuleKind,
    RuleTargetType,
    SkinConcern,
    EvidenceType,
)


class EvidenceGapsCommandTests(TestCase):
    """Test evidence_gaps management command."""

    def setUp(self):
        # Create test concerns
        self.concern_a = SkinConcern.objects.create(
            slug="concern-a",
            display_name="Concern A",
            consumer_label="A",
        )
        self.concern_b = SkinConcern.objects.create(
            slug="concern-b",
            display_name="Concern B",
            consumer_label="B",
        )

        # Create rules with and without evidence
        self.rule_a_no_evidence = ConcernRule.objects.create(
            concern=self.concern_a,
            key="rule-a-1",
            label="Rule A1",
            rule_kind=RuleKind.PENALIZE,
            target_type=RuleTargetType.FREE_TEXT,
            raw_target="test",
            weight=10,
        )

        self.rule_a_with_evidence = ConcernRule.objects.create(
            concern=self.concern_a,
            key="rule-a-2",
            label="Rule A2",
            rule_kind=RuleKind.BOOST,
            target_type=RuleTargetType.FREE_TEXT,
            raw_target="test",
            weight=10,
        )

        self.rule_b_no_evidence = ConcernRule.objects.create(
            concern=self.concern_b,
            key="rule-b-1",
            label="Rule B1",
            rule_kind=RuleKind.AVOID,
            target_type=RuleTargetType.FREE_TEXT,
            raw_target="test",
            weight=10,
        )

        # Add evidence to rule_a_with_evidence
        ref = LiteratureReference.objects.create(pmid="12345")
        ConcernEvidence.objects.create(
            rule=self.rule_a_with_evidence,
            literature_reference=ref,
            evidence_type=EvidenceType.CLINICAL,
            citation_label="Study",
            source_name="PubMed",
            key="evidence-1",
            is_active=True,
        )

    def test_command_lists_zero_evidence_rules(self):
        """Command lists active rules with zero evidence."""
        out = StringIO()
        call_command("evidence_gaps", stdout=out)
        output = out.getvalue()

        # Should include rules with no evidence
        self.assertIn("concern-a  rule-a-1  penalize", output)
        self.assertIn("concern-b  rule-b-1  avoid", output)

        # Should NOT include rule with evidence
        self.assertNotIn("rule-a-2", output)

    def test_command_groups_by_concern(self):
        """Command output groups rules by concern slug."""
        out = StringIO()
        call_command("evidence_gaps", stdout=out)
        output = out.getvalue()

        lines = output.strip().split("\n")

        # Find lines for each concern
        concern_a_lines = [l for l in lines if l.startswith("concern-a")]
        concern_b_lines = [l for l in lines if l.startswith("concern-b")]

        # Should have the correct rules
        self.assertEqual(len(concern_a_lines), 1)
        self.assertEqual(len(concern_b_lines), 1)

    def test_inactive_rules_ignored(self):
        """Inactive rules are not listed."""
        self.rule_b_no_evidence.is_active = False
        self.rule_b_no_evidence.save()

        out = StringIO()
        call_command("evidence_gaps", stdout=out)
        output = out.getvalue()

        # Should NOT include inactive rule
        self.assertNotIn("rule-b-1", output)

    def test_no_zero_evidence_rules_message(self):
        """When no zero-evidence rules exist, show completion message."""
        # Deactivate zero-evidence rules
        self.rule_a_no_evidence.is_active = False
        self.rule_a_no_evidence.save()
        self.rule_b_no_evidence.is_active = False
        self.rule_b_no_evidence.save()

        out = StringIO()
        call_command("evidence_gaps", stdout=out)
        output = out.getvalue()

        # Should show success message
        self.assertIn("No rules with zero evidence found", output)
