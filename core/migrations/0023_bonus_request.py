# BonusRequest model: user bonus claim requests (mirror Deposit/Withdraw)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_game_is_single_game'),
    ]

    operations = [
        migrations.CreateModel(
            name='BonusRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=16)),
                ('bonus_type', models.CharField(choices=[('welcome', 'Welcome'), ('deposit', 'Deposit'), ('referral', 'Referral')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('reject_reason', models.TextField(blank=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('remarks', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bonus_rule', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bonus_requests', to='core.bonusrule')),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bonus_requests_processed', to='core.user')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bonus_requests', to='core.user')),
            ],
            options={
                'verbose_name': 'Bonus Request',
                'verbose_name_plural': 'Bonus Requests',
            },
        ),
    ]
