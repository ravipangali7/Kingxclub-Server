from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0053_remove_game_and_site_coming_soon_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesetting',
            name='scrolling_text',
            field=models.TextField(blank=True, default=''),
        ),
    ]
