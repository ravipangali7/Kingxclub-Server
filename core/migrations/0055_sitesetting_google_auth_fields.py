from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0054_sitesetting_scrolling_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesetting',
            name='google_auth_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='google_client_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='google_client_secret',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='sitesetting',
            name='google_redirect_uri',
            field=models.URLField(blank=True),
        ),
    ]
