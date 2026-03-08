# Game launch per doc: per-provider api_endpoint, api_secret, api_token

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_forgot_password_otp'),
    ]

    operations = [
        migrations.AddField(
            model_name='gameprovider',
            name='api_endpoint',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='gameprovider',
            name='api_secret',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='gameprovider',
            name='api_token',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
