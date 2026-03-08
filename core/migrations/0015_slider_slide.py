# SliderSlide model for second home slider

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_signup_otp_session_super_setting_sms'),
    ]

    operations = [
        migrations.CreateModel(
            name='SliderSlide',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=500)),
                ('subtitle', models.CharField(blank=True, max_length=500)),
                ('image', models.CharField(blank=True, max_length=1000)),
                ('cta_label', models.CharField(default='Join Now', max_length=100)),
                ('cta_link', models.CharField(default='/register', max_length=500)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['order', 'id'],
                'verbose_name': 'Slider Slide',
                'verbose_name_plural': 'Slider Slides',
            },
        ),
    ]
