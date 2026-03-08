# Transaction.game_log FK and audit link to GameLog

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_add_home_content_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='game_log',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='transactions',
                to='core.gamelog',
            ),
        ),
    ]
