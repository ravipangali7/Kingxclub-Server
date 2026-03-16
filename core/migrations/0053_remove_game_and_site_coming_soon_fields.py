# Remove Game coming-soon fields and SiteSetting.site_coming_soon_json

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0052_comingsoon'),
    ]

    operations = [
        migrations.RemoveField(model_name='game', name='coming_soon_description'),
        migrations.RemoveField(model_name='game', name='coming_soon_image'),
        migrations.RemoveField(model_name='game', name='coming_soon_launch_date'),
        migrations.RemoveField(model_name='game', name='is_coming_soon'),
        migrations.RemoveField(model_name='sitesetting', name='site_coming_soon_json'),
    ]
