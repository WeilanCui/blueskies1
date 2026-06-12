import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_brand_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="formulationingredient",
            name="functional_classes_override",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="formulationingredient",
            name="function_override_source",
            field=models.CharField(
                blank=True,
                choices=[
                    ("computed", "Computed (RDKit, rules)"),
                    ("regulatory", "Regulatory (CosIng, CIR)"),
                    ("literature", "Literature / RAG"),
                    ("aggregator", "Third-party aggregator (INCI API)"),
                    ("agent", "Agent inference"),
                    ("human", "Human review"),
                    ("seed", "Reference seed data"),
                ],
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="formulationingredient",
            name="function_override_confidence",
            field=models.FloatField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0.0),
                    django.core.validators.MaxValueValidator(1.0),
                ],
            ),
        ),
        migrations.AddField(
            model_name="formulationingredient",
            name="function_override_notes",
            field=models.TextField(blank=True),
        ),
    ]
