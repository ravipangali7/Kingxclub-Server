# Add Game coming soon fields for dynamic Coming Soon section

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_add_message_is_read'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='is_coming_soon',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='game',
            name='coming_soon_launch_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='game',
            name='coming_soon_description',
            field=models.TextField(blank=True),
        ),
    ]
