

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Amizade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_amizade', models.DateTimeField(default=django.utils.timezone.now)),
                ('usuario1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='amizades1', to=settings.AUTH_USER_MODEL)),
                ('usuario2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='amizades2', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-data_amizade',),
                'unique_together': {('usuario1', 'usuario2')},
            },
        ),
        migrations.CreateModel(
            name='PedidoAmizade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_criacao', models.DateTimeField(default=django.utils.timezone.now)),
                ('aceito', models.BooleanField(default=False)),
                ('de_usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pedidos_de_enviados', to=settings.AUTH_USER_MODEL)),
                ('para_usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pedidos_de_recebidos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-data_criacao',),
                'unique_together': {('de_usuario', 'para_usuario')},
            },
        ),
    ]
