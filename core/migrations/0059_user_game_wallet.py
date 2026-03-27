from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0058_alter_supersetting_reject_reason_suggestions'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='game_wallet',
            field=models.CharField(blank=True, default='main', max_length=10),
        ),
    ]
