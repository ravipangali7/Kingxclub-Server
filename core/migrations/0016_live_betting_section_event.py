# LiveBettingSection and LiveBettingEvent models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_slider_slide'),
    ]

    operations = [
        migrations.CreateModel(
            name='LiveBettingSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['order', 'id'],
                'verbose_name': 'Live Betting Section',
                'verbose_name_plural': 'Live Betting Sections',
            },
        ),
        migrations.CreateModel(
            name='LiveBettingEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sport', models.CharField(blank=True, max_length=100)),
                ('team1', models.CharField(max_length=255)),
                ('team2', models.CharField(max_length=255)),
                ('event_date', models.CharField(blank=True, max_length=50)),
                ('event_time', models.CharField(blank=True, max_length=20)),
                ('odds', models.JSONField(blank=True, default=list)),
                ('is_live', models.BooleanField(default=False)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='core.livebettingsection')),
            ],
            options={
                'ordering': ['section', 'order', 'id'],
                'verbose_name': 'Live Betting Event',
                'verbose_name_plural': 'Live Betting Events',
            },
        ),
    ]
