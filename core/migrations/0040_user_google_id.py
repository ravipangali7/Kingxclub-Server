"""Add google_id to User for Google OAuth login."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0039_remove_paymentmode_legacy_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="google_id",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
    ]
