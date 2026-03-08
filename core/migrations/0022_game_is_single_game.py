# Add is_single_game to Game: when true, provider click opens that game directly

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_gameprovider_banner'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='is_single_game',
            field=models.BooleanField(default=False),
        ),
    ]
