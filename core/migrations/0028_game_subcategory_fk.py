# Add nullable subcategory FK to Game model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_add_game_subcategory_and_game_flags'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='subcategory',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='games',
                to='core.gamesubcategory',
            ),
        ),
    ]
