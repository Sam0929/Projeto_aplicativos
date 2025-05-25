# treinos/management/commands/populate_initial_data.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from treinos.models import Treino, GrupoMuscular, Exercicio, ExecucaoTreino, ExecucaoExercicio, CompartilhamentoTreino
from users.models import Profile
from amizades.models import Amizade, PedidoAmizade, PersonalInvite
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Popula o banco com 10 usuários (alguns personal, alguns comuns) e alguns treinos de exemplo.'

    def handle(self, *args, **options):
        # 1) Vamos excluir tudo que já existe para começar “limpo”:
        self.stdout.write(self.style.WARNING('Excluindo dados existentes...'))

        # Note que a ordem de exclusão deve respeitar integridade referencial:
        ExecucaoExercicio.objects.all().delete()
        ExecucaoTreino.objects.all().delete()
        Exercicio.objects.all().delete()
        GrupoMuscular.objects.all().delete()
        Treino.objects.all().delete()
        CompartilhamentoTreino.objects.all().delete()

        PersonalInvite.objects.all().delete()
        Amizade.objects.all().delete()
        PedidoAmizade.objects.all().delete()

        Profile.objects.all().delete()
        User.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('Banco de dados limpo.'))

        # 2) Criar 10 usuários com nomes “reais” e perfis
        nomes = [
            ('Carlos Silva', 'carlos.silva@example.com'),
            ('Ana Pereira', 'ana.pereira@example.com'),
            ('Mariana Costa', 'mariana.costa@example.com'),
            ('Roberto Souza', 'roberto.souza@example.com'),
            ('Fernanda Gomes', 'fernanda.gomes@example.com'),
            ('Lucas Oliveira', 'lucas.oliveira@example.com'),
            ('Beatriz Lima', 'beatriz.lima@example.com'),
            ('Pedro Fernandes', 'pedro.fernandes@example.com'),
            ('Patrícia Rocha', 'patricia.rocha@example.com'),
            ('Eduardo Santos', 'eduardo.santos@example.com'),
        ]

        self.stdout.write('Criando 10 usuários (alguns personal, alguns comuns)…')
        usuarios = []
        for idx, (nome, email) in enumerate(nomes, start=1):
            username = email.split('@')[0]  # ex: "carlos.silva"
            password = 'senha1234'          # todos terão a mesma senha de teste
            # 2.1) Usuário
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': nome.split()[0],
                    'last_name': ' '.join(nome.split()[1:]),
                }
            )
            if created:
                user.set_password(password)
                user.save()

            # 2.2) Perfil
            # Se já existir, apenas atualiza; se não existir, cria
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.age = random.randint(18, 50)
            profile.weight = round(random.uniform(60, 90), 1)
            profile.height = round(random.uniform(160, 190), 1)
            profile.experience_years = round(random.uniform(0.5, 5.0), 1)
            profile.bio = f"Olá, eu sou {nome} e adoro treinar!"
            profile.location = random.choice(['São Paulo', 'Rio de Janeiro', 'Belo Horizonte', 'Curitiba'])
            profile.show_age = True
            profile.show_weight = True
            profile.show_height = True
            profile.show_experience = True

            # Tornar alguns aleatoriamente “personal trainers”
            if idx % 3 == 0:
                profile.is_personal = True
                profile.college = random.choice([
                    'Faculdade de Educação Física - FEEX',
                    'Universidade Federal de São Paulo - UNIFESP',
                    'Centro Universitário de Treinamento - CETRENO'
                ])
                profile.certifications = "CREF 12345-SP; Curso de Treinamento Funcional; Pós em Nutrição Esportiva"
            else:
                profile.is_personal = False
                profile.college = ''
                profile.certifications = ''

            profile.hide_email = False
            profile.save()

            usuarios.append(user)

        self.stdout.write(self.style.SUCCESS('10 usuários criados com sucesso.'))

        # 3) Criar amizades entre alguns deles
        self.stdout.write('Criando algumas amizades de exemplo...')
        for i in range(0, 8, 2):
            u1 = usuarios[i]
            u2 = usuarios[i+1]
            # Garante ordem (id menor primeiro)
            primeiro, segundo = (u1, u2) if u1.id < u2.id else (u2, u1)
            Amizade.objects.create(usuario1=primeiro, usuario2=segundo)

        self.stdout.write(self.style.SUCCESS('Amizades criadas.'))

        # 4) Criar convites de Personal → aluno (PersonalInvite)
        self.stdout.write('Enviando convites de personal para alguns usuários…')
        personais = [u for u in usuarios if u.profile.is_personal]
        comuns = [u for u in usuarios if not u.profile.is_personal]

        # Cada personal convida aleatoriamente 1 ou 2 “comuns” para serem alunos
        for personal in personais:
            convidados = random.sample(comuns, k=2 if len(comuns) >= 2 else 1)
            for aluno in convidados:
                invite, created = PersonalInvite.objects.get_or_create(
                    personal=personal,
                    para_usuario=aluno
                )
                if created:
                    invite.aceito = False
                    invite.save()

        self.stdout.write(self.style.SUCCESS('Convites de Personal enviados.'))

        # 5) Criar alguns treinos para cada usuário “comum” (Execução futura de exemplo)
        self.stdout.write('Criando treinos de exemplo para usuá­rios “comuns”…')
        for usuario in comuns:
            # criar 2 treinos de cada um
            for tnum in range(1, 3):
                treino = Treino.objects.create(
                    nome=f"Treino {tnum} de {usuario.first_name}",
                    usuario=usuario,
                    duracao=timedelta(minutes=random.randint(30, 75)),
                    carga_total=round(random.uniform(50, 150), 1)
                )

                # para cada treino, criar 2 grupos musculares
                for gnum in range(1, 3):
                    grupo = GrupoMuscular.objects.create(
                        treino=treino,
                        nome=f"Grupo {gnum}"
                    )
                    # em cada grupo, 2 exercícios
                    for exnum in range(1, 3):
                        Exercicio.objects.create(
                            grupo=grupo,
                            nome=f"Ex. {exnum} ({grupo.nome})",
                            series=random.randint(3, 5),
                            repeticoes=random.randint(8, 12),
                            descanso=random.randint(30, 90),
                            carga_maxima=round(random.uniform(20, 80), 1)
                        )

        self.stdout.write(self.style.SUCCESS('Treinos de exemplo criados.'))

        # 6) Criar algumas execuções desses treinos (ExecucaoTreino e ExecucaoExercicio)
        self.stdout.write('Criando histórico de execuções de treino…')
        todos_treinos = Treino.objects.all()
        for treino in todos_treinos:
            # cada treino terá entre 1 e 3 execuções
            for runnum in range(random.randint(1, 3)):
                et = ExecucaoTreino.objects.create(
                    treino=treino,
                    usuario=treino.usuario,
                    data_inicio=timezone.now() - timedelta(days=random.randint(1, 30)),
                    duracao=timedelta(minutes=random.randint(25, 70)),
                    carga_total=round(random.uniform(40, treino.carga_total), 1)
                )
                # cada execução, registra 2 ExecucaoExercicio (um para cada Exercicio existente)
                exercicios_do_treino = Exercicio.objects.filter(grupo__treino=treino)
                for ex in exercicios_do_treino:
                    ExecucaoExercicio.objects.create(
                        execucao_treino=et,
                        exercicio=ex,
                        serie=random.randint(1, ex.series),
                        carga_utilizada=round(random.uniform(0.5 * ex.carga_maxima, ex.carga_maxima), 1),
                        duracao=timedelta(seconds=random.randint(30, 120))
                    )

        self.stdout.write(self.style.SUCCESS('Execuções de treino criadas.'))

        # 7) Criar alguns compartilhamentos de treino (CompartilhamentoTreino)
        self.stdout.write('Criando compartilhamentos de treino…')
        # cada usuário “comum” compartilha seu primeiro treino com outro usuário “comum” aleatório
        for usuario in comuns:
            treinos_do_usuario = Treino.objects.filter(usuario=usuario)
            if treinos_do_usuario.exists():
                treino = treinos_do_usuario.first()
                outro = random.choice([u for u in comuns if u != usuario])
                CompartilhamentoTreino.objects.get_or_create(
                    treino=treino,
                    de_usuario=usuario,
                    para_usuario=outro,
                    defaults={'aceito': False}
                )

        self.stdout.write(self.style.SUCCESS('Compartilhamentos de treino criados.'))

        self.stdout.write(self.style.SUCCESS('POPULAÇÃO INICIAL CONCLUÍDA COM SUCESSO!'))
