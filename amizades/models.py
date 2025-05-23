from django.db import models

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q

User = get_user_model()

class PedidoAmizade(models.Model):
    """
    Representa um pedido de amizade de um usuário para outro.
    Após aceitação, criamos uma amizade mútua.
    """
    de_usuario = models.ForeignKey(
        User,
        related_name='pedidos_de_enviados',
        on_delete=models.CASCADE
    )
    para_usuario = models.ForeignKey(
        User,
        related_name='pedidos_de_recebidos',
        on_delete=models.CASCADE
    )
    data_criacao = models.DateTimeField(default=timezone.now)
    aceito = models.BooleanField(default=False)
    # Você pode adicionar “rejeitado” ou outros estados se quiser.

    class Meta:
        unique_together = ('de_usuario', 'para_usuario')
        ordering = ('-data_criacao',)

    def __str__(self):
        return f"Pedido de {self.de_usuario.username} → {self.para_usuario.username} (aceito={self.aceito})"


class Amizade(models.Model):
    """
    Representa uma amizade _mútua_ entre dois usuários.
    Sempre que um pedido for aceito, criaremos uma instância de Amizade (apenas um registro),
    e utilizaremos convenção de user1.id < user2.id para não duplicar.
    """
    usuario1 = models.ForeignKey(
        User,
        related_name='amizades1',
        on_delete=models.CASCADE
    )
    usuario2 = models.ForeignKey(
        User,
        related_name='amizades2',
        on_delete=models.CASCADE
    )
    data_amizade = models.DateTimeField(default=timezone.now)

    class Meta:
        # Garante que não existam duplicatas (1,2) e (2,1)
        unique_together = (('usuario1', 'usuario2'),)
        ordering = ('-data_amizade',)

    def __str__(self):
        return f"Amizade: {self.usuario1.username} ↔ {self.usuario2.username}"

    @classmethod
    def criar_amizade_mutua(cls, u1, u2):
        """
        Garante que usuario1.id < usuario2.id antes de criar,
        para padronizar (assim não haverá duplicatas invertidas).
        """
        if u1.id == u2.id:
            raise ValueError("Não é possível criar amizade com o mesmo usuário.")
        # normaliza a ordem
        primeiro, segundo = (u1, u2) if u1.id < u2.id else (u2, u1)
        amizade, criada = cls.objects.get_or_create(usuario1=primeiro, usuario2=segundo)
        return amizade


class PersonalInvite(models.Model):
    """
    Convite que um Personal envia a um usuário para torná-lo seu aluno.
    """
    personal = models.ForeignKey(
        User,
        related_name='convites_enviados',
        on_delete=models.CASCADE
    )
    para_usuario = models.ForeignKey(
        User,
        related_name='convites_recebidos',
        on_delete=models.CASCADE
    )
    criado_em = models.DateTimeField(default=timezone.now)
    aceito = models.BooleanField(default=False)

    class Meta:
        unique_together = ('personal', 'para_usuario')
        ordering = ('-criado_em',)

    def __str__(self):
        return f"{self.personal.username} → {self.para_usuario.username} (aceito={self.aceito})"