from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0056_reference_ids_reject_suggestions'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='whatsapp_deposit',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='user',
            name='whatsapp_withdraw',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
