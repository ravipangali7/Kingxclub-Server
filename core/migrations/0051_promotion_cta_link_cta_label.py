# Add cta_link and cta_label to Promotion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0050_paymentmode_status_default_approved'),
    ]

    operations = [
        migrations.AddField(
            model_name='promotion',
            name='cta_link',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='promotion',
            name='cta_label',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
