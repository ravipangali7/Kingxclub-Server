"""Add home page section JSON fields to SiteSetting."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0031_add_payment_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesetting",
            name="site_categories_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="site_top_games_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="site_providers_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="site_categories_game_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="site_popular_games_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="site_coming_soon_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="site_refer_bonus_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="site_payments_accepted_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="site_footer_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="site_welcome_deposit_json",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
