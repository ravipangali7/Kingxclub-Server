# ComingSoonEnrollment: user notify for coming-soon games

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_popup'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComingSoonEnrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='coming_soon_enrollments', to='core.game')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='coming_soon_enrollments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Coming Soon Enrollment',
                'verbose_name_plural': 'Coming Soon Enrollments',
            },
        ),
        migrations.AddConstraint(
            model_name='comingsoonenrollment',
            constraint=models.UniqueConstraint(fields=('game', 'user'), name='unique_coming_soon_enrollment'),
        ),
    ]
