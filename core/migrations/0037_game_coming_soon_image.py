"""Add coming_soon_image to Game."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0036_sitesetting_site_theme_json"),
    ]

    operations = [
        migrations.AddField(
            model_name="game",
            name="coming_soon_image",
            field=models.ImageField(blank=True, null=True, upload_to="games/"),
        ),
    ]
