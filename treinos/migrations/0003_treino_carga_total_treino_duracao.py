# Generated by Django 5.2 on 2025-04-19 04:50

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('treinos', '0002_remove_treino_descricao_grupomuscular_exercicio'),
    ]

    operations = [
        migrations.AddField(
            model_name='treino',
            name='carga_total',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='treino',
            name='duracao',
            field=models.DurationField(default=datetime.timedelta(0)),
        ),
    ]
