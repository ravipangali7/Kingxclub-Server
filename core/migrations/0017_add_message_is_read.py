# Add Message.is_read for unread count / sidebar badges

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_live_betting_section_event'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
    ]
