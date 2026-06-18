# Generated for generic literature discovery work items and event outbox.

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


def populate_existing_target_labels(apps, schema_editor):
    LiteratureDiscoveryTarget = apps.get_model("core", "LiteratureDiscoveryTarget")

    for target in LiteratureDiscoveryTarget.objects.select_related("compound").filter(
        target_type="compound",
        compound__isnull=False,
    ):
        compound = target.compound
        search_label = target.search_label or compound.display_name or compound.canonical_inci
        LiteratureDiscoveryTarget.objects.filter(pk=target.pk).update(
            search_label=search_label,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_literaturediscoverytarget"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="literaturediscoverytarget",
            name="unique_active_literature_discovery_per_compound",
        ),
        migrations.AddField(
            model_name="literaturediscoverytarget",
            name="target_type",
            field=models.CharField(
                choices=[
                    ("compound", "Compound"),
                    ("formulation", "Formulation"),
                    ("product", "Product"),
                ],
                default="compound",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="literaturediscoverytarget",
            name="formulation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="literature_discovery_targets",
                to="core.formulation",
            ),
        ),
        migrations.AddField(
            model_name="literaturediscoverytarget",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="literature_discovery_targets",
                to="core.product",
            ),
        ),
        migrations.AddField(
            model_name="literaturediscoverytarget",
            name="search_label",
            field=models.CharField(blank=True, max_length=512),
        ),
        migrations.AlterField(
            model_name="literaturediscoverytarget",
            name="compound",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="literature_discovery_targets",
                to="core.compound",
            ),
        ),
        migrations.RunPython(
            populate_existing_target_labels,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.CreateModel(
            name="LiteratureDiscoveryEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            (
                                "compound.created_from_product",
                                "Compound created from product",
                            ),
                            (
                                "compound.created_from_formulation",
                                "Compound created from formulation",
                            ),
                            ("compound.resolved_from_inci", "Compound resolved from INCI"),
                            (
                                "mixture.created_from_product",
                                "Mixture created from product",
                            ),
                            (
                                "mixture.created_from_formulation",
                                "Mixture created from formulation",
                            ),
                            ("mixture.resolved_from_inci", "Mixture resolved from INCI"),
                            ("formulation.created", "Formulation created"),
                            ("product.created", "Product created"),
                        ],
                        max_length=64,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processed", "Processed"),
                            ("failed", "Failed"),
                            ("skipped", "Skipped"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                (
                    "target_type",
                    models.CharField(
                        choices=[
                            ("compound", "Compound"),
                            ("formulation", "Formulation"),
                            ("product", "Product"),
                        ],
                        default="compound",
                        max_length=32,
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("new_compound", "New compound"),
                            ("new_mixture", "New mixture"),
                            ("manual_review", "Manual review"),
                            ("retry", "Retry"),
                        ],
                        default="new_compound",
                        max_length=32,
                    ),
                ),
                ("priority", models.IntegerField(default=0)),
                ("search_label", models.CharField(blank=True, max_length=512)),
                ("triggered_by", models.CharField(blank=True, max_length=128)),
                ("source_ref", models.CharField(blank=True, max_length=512)),
                (
                    "dedupe_key",
                    models.CharField(blank=True, max_length=512, null=True, unique=True),
                ),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "compound",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="literature_discovery_events",
                        to="core.compound",
                    ),
                ),
                (
                    "formulation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="literature_discovery_events",
                        to="core.formulation",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="literature_discovery_events",
                        to="core.product",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="literaturediscoverytarget",
            index=models.Index(
                fields=["target_type", "status", "created_at"],
                name="core_litdt_ttype_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="literaturediscoveryevent",
            index=models.Index(
                fields=["status", "created_at"],
                name="core_litde_status_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="literaturediscoveryevent",
            index=models.Index(
                fields=["target_type", "status", "created_at"],
                name="core_litde_ttype_status_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="literaturediscoverytarget",
            constraint=models.CheckConstraint(
                check=(
                    Q(
                        compound__isnull=False,
                        formulation__isnull=True,
                        product__isnull=True,
                        target_type="compound",
                    )
                    | Q(
                        compound__isnull=True,
                        formulation__isnull=False,
                        product__isnull=True,
                        target_type="formulation",
                    )
                    | Q(
                        compound__isnull=True,
                        formulation__isnull=True,
                        product__isnull=False,
                        target_type="product",
                    )
                ),
                name="literature_discovery_target_exactly_one_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="literaturediscoverytarget",
            constraint=models.UniqueConstraint(
                condition=Q(
                    ("status__in", ["pending", "running"]),
                    ("target_type", "compound"),
                    ("compound__isnull", False),
                ),
                fields=("compound",),
                name="unique_active_literature_discovery_per_compound",
            ),
        ),
        migrations.AddConstraint(
            model_name="literaturediscoverytarget",
            constraint=models.UniqueConstraint(
                condition=Q(
                    ("status__in", ["pending", "running"]),
                    ("target_type", "formulation"),
                    ("formulation__isnull", False),
                ),
                fields=("formulation",),
                name="unique_active_literature_discovery_per_formulation",
            ),
        ),
        migrations.AddConstraint(
            model_name="literaturediscoverytarget",
            constraint=models.UniqueConstraint(
                condition=Q(
                    ("status__in", ["pending", "running"]),
                    ("target_type", "product"),
                    ("product__isnull", False),
                ),
                fields=("product",),
                name="unique_active_literature_discovery_per_product",
            ),
        ),
        migrations.AddConstraint(
            model_name="literaturediscoveryevent",
            constraint=models.CheckConstraint(
                check=(
                    Q(
                        compound__isnull=False,
                        formulation__isnull=True,
                        product__isnull=True,
                        target_type="compound",
                    )
                    | Q(
                        compound__isnull=True,
                        formulation__isnull=False,
                        product__isnull=True,
                        target_type="formulation",
                    )
                    | Q(
                        compound__isnull=True,
                        formulation__isnull=True,
                        product__isnull=False,
                        target_type="product",
                    )
                ),
                name="literature_discovery_event_exactly_one_target",
            ),
        ),
    ]
