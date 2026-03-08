"""Add site_theme_json to SiteSetting for dynamic website/player colors."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0035_game_remove_is_single_game_add_is_lobby"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesetting",
            name="site_theme_json",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
