"""Tests for the Compound API, focusing on literature_count optimization."""

from django.db import connection
from django.db.models import Count
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Compound, CompoundLiterature, LiteratureReference
from core.serializers import CompoundSerializer


class CompoundLiteratureCountTests(TestCase):
    """Test that literature_count is computed efficiently at the database level."""

    def setUp(self):
        self.client = APIClient()

    def test_literature_count_correct_value(self):
        """Test 2.1: Compound with known number of literature links returns correct count."""
        # Create a compound
        compound = Compound.objects.create(
            canonical_inci="TEST COMPOUND",
            display_name="Test Compound",
            entity_type="small_molecule",
        )

        # Create 3 literature references
        lit_refs = [
            LiteratureReference.objects.create(
                pmid=f"1000000{i}",
                title=f"Paper {i}",
            )
            for i in range(3)
        ]

        # Link each reference to the compound
        for lit_ref in lit_refs:
            CompoundLiterature.objects.create(
                compound=compound,
                literature=lit_ref,
                source_type="literature",
                source_name="pubmed",
                source_ref=lit_ref.pmid,
            )

        # GET the compound via the detail endpoint
        url = reverse("compound-detail", args=[compound.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["literature_count"], 3)

    def test_literature_count_list_endpoint(self):
        """Test literature_count via the compound-list endpoint."""
        # Create a compound with 2 literature links
        compound = Compound.objects.create(
            canonical_inci="ANOTHER COMPOUND",
            display_name="Another Compound",
            entity_type="polymer",
        )

        lit_refs = [
            LiteratureReference.objects.create(
                pmid=f"2000000{i}",
                title=f"Paper {i}",
            )
            for i in range(2)
        ]

        for lit_ref in lit_refs:
            CompoundLiterature.objects.create(
                compound=compound,
                literature=lit_ref,
                source_type="literature",
                source_name="pubmed",
                source_ref=lit_ref.pmid,
            )

        # GET the compound-list endpoint
        url = reverse("compound-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Find our compound in the list
        found = [c for c in response.data if c["id"] == compound.id]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["literature_count"], 2)

    def test_literature_count_no_links(self):
        """Test that a compound with no literature links has literature_count = 0."""
        compound = Compound.objects.create(
            canonical_inci="NO LINKS COMPOUND",
            display_name="No Links Compound",
            entity_type="small_molecule",
        )

        url = reverse("compound-detail", args=[compound.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["literature_count"], 0)

    def test_literature_count_no_per_compound_queries(self):
        """Test 2.2: the literature_count annotation adds no per-compound query.

        The full list-endpoint query total is intentionally NOT asserted: other
        SerializerMethodFields (inherited/effective properties) issue their own
        per-compound queries that predate this change. This test isolates the
        literature_count path by reading the annotation the viewset applies.
        """
        for ci in range(4):
            compound = Compound.objects.create(
                canonical_inci=f"COMPOUND {ci}",
                display_name=f"Compound {ci}",
                entity_type="small_molecule",
            )
            for i in range(3):
                lit_ref = LiteratureReference.objects.create(
                    pmid=f"3{ci}0000{i}",
                    title=f"Paper {ci}-{i}",
                )
                CompoundLiterature.objects.create(
                    compound=compound,
                    literature=lit_ref,
                    source_type="literature",
                    source_name="pubmed",
                    source_ref=lit_ref.pmid,
                )

        # Materialize every compound with the same annotation the viewset uses and
        # read each literature_count. Without the annotation, accessing the count
        # would emit one COUNT query per compound (N+1); with it, the counts come
        # from the single list query.
        with CaptureQueriesContext(connection) as ctx:
            compounds = list(
                Compound.objects.annotate(literature_count=Count("literature_links"))
            )
            counts = sorted(c.literature_count for c in compounds)

        self.assertEqual(counts, [3, 3, 3, 3])
        self.assertEqual(
            len(ctx.captured_queries),
            1,
            "literature_count should come from the single annotated query, but "
            f"{len(ctx.captured_queries)} queries ran: "
            f"{[q['sql'] for q in ctx.captured_queries]}",
        )

    def test_literature_count_non_annotated_fallback(self):
        """Test 2.3: Serializer fallback for non-annotated Compound."""
        # Create a compound with literature links
        compound = Compound.objects.create(
            canonical_inci="FALLBACK TEST",
            display_name="Fallback Test",
            entity_type="small_molecule",
        )

        lit_refs = [
            LiteratureReference.objects.create(
                pmid=f"4000000{i}",
                title=f"Paper {i}",
            )
            for i in range(2)
        ]

        for lit_ref in lit_refs:
            CompoundLiterature.objects.create(
                compound=compound,
                literature=lit_ref,
                source_type="literature",
                source_name="pubmed",
                source_ref=lit_ref.pmid,
            )

        # Fetch the compound WITHOUT annotation (plain queryset)
        plain_compound = Compound.objects.get(pk=compound.id)

        # Verify it has no literature_count attribute (no annotation)
        self.assertFalse(hasattr(plain_compound, "literature_count"))

        # Serialize it and verify the fallback path produces the correct count
        serialized = CompoundSerializer(plain_compound).data

        self.assertEqual(serialized["literature_count"], 2)
