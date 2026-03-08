"""Remove legacy fields from PaymentMode; use only payment_method + details."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0038_paymentmode_payment_method_and_details"),
    ]

    operations = [
        migrations.RemoveField(model_name="paymentmode", name="name"),
        migrations.RemoveField(model_name="paymentmode", name="type"),
        migrations.RemoveField(model_name="paymentmode", name="wallet_phone"),
        migrations.RemoveField(model_name="paymentmode", name="bank_name"),
        migrations.RemoveField(model_name="paymentmode", name="bank_branch"),
        migrations.RemoveField(model_name="paymentmode", name="bank_account_no"),
        migrations.RemoveField(model_name="paymentmode", name="bank_account_holder_name"),
    ]
