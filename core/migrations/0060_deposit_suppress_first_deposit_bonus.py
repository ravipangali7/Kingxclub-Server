from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0059_user_game_wallet'),
    ]

    operations = [
        migrations.AddField(
            model_name='deposit',
            name='suppress_first_deposit_bonus',
            field=models.BooleanField(default=False),
        ),
    ]
