# Generated migration: add icon ImageField to GameCategory

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_sitesetting_home_json_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamecategory',
            name='icon',
            field=models.ImageField(blank=True, null=True, upload_to='categories/'),
        ),
    ]
