# Generated by Django 5.2 on 2025-05-25 17:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('treinos', '0009_rename_data_compartilhamento_compartilhamentotreino_criado_em_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='treino',
            name='is_padrao',
            field=models.BooleanField(default=False),
        ),
    ]
