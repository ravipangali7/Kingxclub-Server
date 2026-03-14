# Default new payment modes to approved

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_transaction_processed_by'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentmode',
            name='status',
            field=models.CharField(
                choices=[('approved', 'Approved'), ('pending', 'Pending'), ('rejected', 'Rejected')],
                default='approved',
                max_length=20,
            ),
        ),
    ]
