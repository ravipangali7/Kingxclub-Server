# Add reference_id to Deposit

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0044_message_message_blank"),
    ]

    operations = [
        migrations.AddField(
            model_name="deposit",
            name="reference_id",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
