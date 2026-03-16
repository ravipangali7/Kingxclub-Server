# New ComingSoon model for home page coming soon section

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_promotion_cta_link_cta_label'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComingSoon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('image', models.ImageField(blank=True, null=True, upload_to='coming_soon/')),
                ('description', models.TextField(blank=True)),
                ('coming_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Coming Soon',
                'verbose_name_plural': 'Coming Soon',
                'ordering': ['coming_date', 'id'],
            },
        ),
    ]
