"""Add country_code to User."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0040_user_google_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="country_code",
            field=models.CharField(blank=True, max_length=5),
        ),
    ]
