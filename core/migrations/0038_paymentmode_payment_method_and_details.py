"""Add payment_method FK and details JSON to PaymentMode; make name/type optional for migration."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0037_game_coming_soon_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentmode",
            name="payment_method",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="payment_modes",
                to="core.paymentmethod",
            ),
        ),
        migrations.AddField(
            model_name="paymentmode",
            name="details",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="paymentmode",
            name="name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="paymentmode",
            name="type",
            field=models.CharField(blank=True, choices=[("ewallet", "E-Wallet"), ("bank", "Bank")], max_length=20),
        ),
    ]
