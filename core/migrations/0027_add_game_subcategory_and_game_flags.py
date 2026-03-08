# GameSubCategory model + Game is_top_game, is_popular_game

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_sitesetting_favicon'),
    ]

    operations = [
        migrations.CreateModel(
            name='GameSubCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('svg', models.FileField(blank=True, null=True, upload_to='subcategories/')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('game_category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subcategories', to='core.gamecategory')),
            ],
            options={
                'verbose_name': 'Game Sub Category',
                'verbose_name_plural': 'Game Sub Categories',
            },
        ),
        migrations.AddField(
            model_name='game',
            name='is_top_game',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='game',
            name='is_popular_game',
            field=models.BooleanField(default=False),
        ),
    ]
