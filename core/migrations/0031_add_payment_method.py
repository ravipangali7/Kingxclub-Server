"""Add PaymentMethod model (site-level accepted payment methods)."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0030_remove_gamesubcategory"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentMethod",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("image", models.ImageField(blank=True, null=True, upload_to="payments/")),
                ("fields", models.JSONField(blank=True, default=dict)),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Payment Method",
                "verbose_name_plural": "Payment Methods",
                "ordering": ["order", "id"],
            },
        ),
    ]
