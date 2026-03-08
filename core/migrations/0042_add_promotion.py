# Promotion model for promotional offers / campaigns

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0041_user_country_code"),
    ]

    operations = [
        migrations.CreateModel(
            name="Promotion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=500)),
                ("image", models.ImageField(blank=True, null=True, upload_to="promotions/")),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Promotion",
                "verbose_name_plural": "Promotions",
                "ordering": ["order", "id"],
            },
        ),
    ]
