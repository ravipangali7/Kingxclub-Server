# GameProvider banner field for provider page

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_sliderslide_image_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='gameprovider',
            name='banner',
            field=models.ImageField(blank=True, null=True, upload_to='providers/banners/'),
        ),
    ]
