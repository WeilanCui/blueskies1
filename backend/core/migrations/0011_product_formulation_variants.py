# Generated manually for the Product/Formulation split.

import django.db.models.deletion
from django.db import migrations, models
from django.db.models.functions import Lower


def backfill_products(apps, schema_editor):
    Product = apps.get_model("core", "Product")
    Formulation = apps.get_model("core", "Formulation")

    for formulation in Formulation.objects.all().iterator():
        brand = (formulation.brand or "").strip()
        name = (formulation.name or "").strip() or "Unnamed product"
        product = Product.objects.filter(
            brand__iexact=brand,
            name__iexact=name,
        ).first()
        if product is None:
            product = Product.objects.create(
                brand=brand,
                name=name,
                display_name=name,
                source=formulation.source or "",
                source_ref=formulation.source_ref or "",
            )
        formulation.product_id = product.pk
        formulation.save(update_fields=["product"])


def restore_formulation_names(apps, schema_editor):
    Formulation = apps.get_model("core", "Formulation")

    for formulation in Formulation.objects.select_related("product").all().iterator():
        if formulation.product_id is None:
            continue
        formulation.name = formulation.product.name
        formulation.brand = formulation.product.brand
        formulation.save(update_fields=["name", "brand"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_contactsubmission_user_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Product",
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
                ("brand", models.CharField(blank=True, max_length=256)),
                ("name", models.CharField(max_length=512)),
                ("display_name", models.CharField(blank=True, max_length=512)),
                ("category", models.CharField(blank=True, max_length=128)),
                ("description", models.TextField(blank=True)),
                ("image_url", models.URLField(blank=True, max_length=1024)),
                ("source", models.CharField(blank=True, max_length=64)),
                ("source_ref", models.CharField(blank=True, max_length=512)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["brand", "name"],
                "constraints": [
                    models.UniqueConstraint(
                        Lower("brand"),
                        Lower("name"),
                        name="unique_product_brand_name_ci",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="formulation",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="formulations",
                to="core.product",
            ),
        ),
        migrations.AddField(
            model_name="formulation",
            name="market",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="formulation",
            name="made_in",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="formulation",
            name="version_label",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="formulation",
            name="effective_from",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="formulation",
            name="effective_to",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="formulationingredient",
            name="is_key_active",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="formulationingredient",
            name="active_note",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(backfill_products, restore_formulation_names),
        migrations.AlterField(
            model_name="formulation",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="formulations",
                to="core.product",
            ),
        ),
        migrations.RemoveField(
            model_name="formulation",
            name="brand",
        ),
        migrations.RemoveField(
            model_name="formulation",
            name="name",
        ),
        migrations.AlterModelOptions(
            name="formulation",
            options={
                "ordering": [
                    "product__brand",
                    "product__name",
                    "market",
                    "version_label",
                    "id",
                ]
            },
        ),
    ]
