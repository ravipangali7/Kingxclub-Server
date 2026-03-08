# SiteSetting favicon for dynamic favicon

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_comingsoonenrollment'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesetting',
            name='favicon',
            field=models.ImageField(blank=True, null=True, upload_to='site/'),
        ),
    ]
