# Remove is_single_game, add is_lobby on Game

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_alter_paymentmethod_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='game',
            name='is_single_game',
        ),
        migrations.AddField(
            model_name='game',
            name='is_lobby',
            field=models.BooleanField(default=False),
        ),
    ]
