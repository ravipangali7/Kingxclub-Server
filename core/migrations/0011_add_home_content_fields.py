# Dynamic home page: hero stats, biggest wins, promo banners

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_game_provider_launch_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesetting',
            name='home_stats',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='biggest_wins',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='promo_banners',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
