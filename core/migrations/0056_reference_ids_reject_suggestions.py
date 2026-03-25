from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0055_sitesetting_google_auth_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='supersetting',
            name='reject_reason_suggestions',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='withdraw',
            name='reference_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='transaction',
            name='reference_id',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
