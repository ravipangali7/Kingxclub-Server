# Add wallet (main/bonus) to Withdraw for player withdrawal source

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0045_deposit_reference_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="withdraw",
            name="wallet",
            field=models.CharField(
                choices=[("main", "Main"), ("bonus", "Bonus")],
                default="main",
                max_length=10,
            ),
        ),
    ]
