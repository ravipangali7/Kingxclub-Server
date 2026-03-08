# Allow blank message when file/image attachment is present

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0043_country"),
    ]

    operations = [
        migrations.AlterField(
            model_name="message",
            name="message",
            field=models.TextField(blank=True),
        ),
    ]
