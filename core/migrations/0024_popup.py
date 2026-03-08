# Popup model for site popups/modals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_bonus_request'),
    ]

    operations = [
        migrations.CreateModel(
            name='Popup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=500)),
                ('content', models.TextField(blank=True)),
                ('image', models.CharField(blank=True, max_length=1000)),
                ('image_file', models.ImageField(blank=True, null=True, upload_to='popup/')),
                ('cta_label', models.CharField(default='OK', max_length=100)),
                ('cta_link', models.CharField(default='#', max_length=500)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Popup',
                'verbose_name_plural': 'Popups',
                'ordering': ['order', 'id'],
            },
        ),
    ]
