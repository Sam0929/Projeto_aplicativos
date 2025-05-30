

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('amizades', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonalInvite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(default=django.utils.timezone.now)),
                ('aceito', models.BooleanField(default=False)),
                ('para_usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='convites_recebidos', to=settings.AUTH_USER_MODEL)),
                ('personal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='convites_enviados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-criado_em',),
                'unique_together': {('personal', 'para_usuario')},
            },
        ),
    ]
