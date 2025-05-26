from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

class Treino(models.Model):
    nome = models.CharField(max_length=100)
    criado_em = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    duracao = models.DurationField(default=timedelta(0))
    carga_total = models.FloatField(default=0.0)
    is_padrao = models.BooleanField(default=False)  
    
    @property
    def total_exercicios(self):
        return sum(grupo.exercicio_set.count() for grupo in self.grupomuscular_set.all())

    @property
    def ultima_execucao(self):
       
        return self.criado_em
    
    def duracao_minutos(self):
       
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
    
class ExecucaoTreino(models.Model):
    treino      = models.ForeignKey(Treino, on_delete=models.CASCADE)
    usuario     = models.ForeignKey(User, on_delete=models.CASCADE)
    data_inicio = models.DateTimeField(default=timezone.now)
    duracao     = models.DurationField(default=timedelta(0))
    carga_total = models.FloatField(default=0.0)  

    def __str__(self):
        return f"{self.treino.nome} em {self.data_inicio:%d/%m/%Y %H:%M}"

    @property
    def duracao_minutos(self):
      
        return self.duracao.seconds // 60

class ExecucaoExercicio(models.Model):
    execucao_treino = models.ForeignKey(ExecucaoTreino, on_delete=models.CASCADE)
    exercicio = models.ForeignKey(Exercicio, on_delete=models.CASCADE)
    serie = models.PositiveIntegerField()
    carga_utilizada = models.FloatField()
    duracao = models.DurationField()
    


User = get_user_model()

class CompartilhamentoTreino(models.Model):
    treino = models.ForeignKey('Treino', on_delete=models.CASCADE, related_name='compartilhamentos')
    de_usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compartilhamentos_feitos')
    para_usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compartilhamentos_recebidos')
    criado_em = models.DateTimeField(auto_now_add=True)
    aceito = models.BooleanField(default=False)

    class Meta:
        unique_together = ('treino', 'para_usuario')

    def __str__(self):
        status = "Aceito" if self.aceito else "Pendente"
        return f"{self.de_usuario.username} → {self.para_usuario.username} ({status})"

