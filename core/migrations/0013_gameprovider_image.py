# GameProvider image field for provider logo

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_add_transaction_game_log_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='gameprovider',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='providers/'),
        ),
    ]
