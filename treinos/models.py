from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta

class Treino(models.Model):
    nome = models.CharField(max_length=100)
    criado_em = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    duracao = models.DurationField(default=timedelta(0))
    carga_total = models.FloatField(default=0.0)
    
    @property
    def total_exercicios(self):
        return sum(grupo.exercicio_set.count() for grupo in self.grupomuscular_set.all())

    @property
    def ultima_execucao(self):
        # Por hora, retorna a própria criação — ajuste depois com histórico real
        return self.criado_em
    
    def duracao_minutos(self):
        # Se quiser lidar com dias, some também: self.duracao.days*24*60
        return self.duracao.seconds // 60

    def __str__(self):
        return self.nome
    
class GrupoMuscular(models.Model):
    treino = models.ForeignKey(Treino, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)

class Exercicio(models.Model):
    grupo = models.ForeignKey(GrupoMuscular, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    series = models.PositiveIntegerField()
    repeticoes = models.PositiveIntegerField()
    descanso = models.PositiveIntegerField()
    carga_maxima = models.FloatField(null=True, blank=True)
    
    