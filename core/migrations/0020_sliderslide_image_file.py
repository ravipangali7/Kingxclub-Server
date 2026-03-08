# Add image_file to SliderSlide for file upload

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_merge_20260224_0047'),
    ]

    operations = [
        migrations.AddField(
            model_name='sliderslide',
            name='image_file',
            field=models.ImageField(blank=True, null=True, upload_to='slider/'),
        ),
    ]
