# Country model for currency by country_code

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0042_add_promotion"),
    ]

    operations = [
        migrations.CreateModel(
            name="Country",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("country_code", models.CharField(db_index=True, max_length=10, unique=True)),
                ("currency_symbol", models.CharField(default="₹", max_length=10)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Country",
                "verbose_name_plural": "Countries",
                "ordering": ["name"],
            },
        ),
        migrations.RunPython(
            lambda apps, schema_editor: seed_countries(apps),
            migrations.RunPython.noop,
        ),
    ]


def seed_countries(apps):
    Country = apps.get_model("core", "Country")
    if Country.objects.filter(country_code="977").exists():
        return
    Country.objects.bulk_create([
        Country(name="Nepal", country_code="977", currency_symbol="Rs.", is_active=True),
        Country(name="India", country_code="91", currency_symbol="₹", is_active=True),
    ])
