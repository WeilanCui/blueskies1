# Generated manually for the Brand model split.

import django.db.models.deletion
from django.db import migrations, models
from django.db.models.functions import Lower


def backfill_brands(apps, schema_editor):
    Brand = apps.get_model("core", "Brand")
    Product = apps.get_model("core", "Product")

    brand_ids_by_name: dict[str, int | None] = {"": None}

    for product in Product.objects.all().iterator():
        brand_name = (product.brand or "").strip()
        cache_key = brand_name.casefold()

        if cache_key not in brand_ids_by_name:
            if not brand_name:
                brand_ids_by_name[cache_key] = None
            else:
                brand = Brand.objects.filter(name__iexact=brand_name).first()
                if brand is None:
                    brand = Brand.objects.create(name=brand_name)
                brand_ids_by_name[cache_key] = brand.pk

        product.brand_link_id = brand_ids_by_name[cache_key]
        product.save(update_fields=["brand_link"])


def restore_product_brand_strings(apps, schema_editor):
    Product = apps.get_model("core", "Product")

    for product in Product.objects.select_related("brand_link").all().iterator():
        if product.brand_link_id is None:
            product.brand = ""
        else:
            product.brand = product.brand_link.name
        product.save(update_fields=["brand"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_product_formulation_variants"),
    ]

    operations = [
        migrations.CreateModel(
            name="Brand",
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
                ("name", models.CharField(max_length=256)),
                ("display_name", models.CharField(blank=True, max_length=256)),
                ("description", models.TextField(blank=True)),
                ("website_url", models.URLField(blank=True, max_length=1024)),
                ("image_url", models.URLField(blank=True, max_length=1024)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name"],
                "constraints": [
                    models.UniqueConstraint(
                        Lower("name"),
                        name="unique_brand_name_ci",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="product",
            name="brand_link",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="products",
                to="core.brand",
            ),
        ),
        migrations.RunPython(backfill_brands, restore_product_brand_strings),
        migrations.RemoveConstraint(
            model_name="product",
            name="unique_product_brand_name_ci",
        ),
        migrations.RemoveField(
            model_name="product",
            name="brand",
        ),
        migrations.RenameField(
            model_name="product",
            old_name="brand_link",
            new_name="brand",
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.UniqueConstraint(
                models.F("brand"),
                Lower("name"),
                name="unique_product_brand_name_ci",
            ),
        ),
        migrations.AlterModelOptions(
            name="product",
            options={"ordering": ["brand__name", "name"]},
        ),
        migrations.AlterModelOptions(
            name="formulation",
            options={
                "ordering": [
                    "product__brand__name",
                    "product__name",
                    "market",
                    "version_label",
                    "id",
                ]
            },
        ),
    ]
