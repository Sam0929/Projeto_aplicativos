from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import PedidoAmizade, Amizade
from django.db.models import Q
from .models import Amizade, PedidoAmizade, PersonalInvite
from amizades import models



User = get_user_model()

@login_required
def adicionar_ou_enviar_pedido(request):
    """
    GET:
      - ?username=texto → busca todos os usuários cujo username contenha 'texto', exceto request.user.
      - Monta um set de friend_ids para ocultar “Enviar Pedido” se já forem amigos.

    POST:
      - target_username = username exato do usuário selecionado → cria PedidoAmizade ou aceita automaticamente.
    """
    # ----------------------------------------------------------------
    # 1) Processa envio de pedido, se for POST
    # ----------------------------------------------------------------
    if request.method == 'POST':
        target_username = request.POST.get('target_username')
        if target_username == request.user.username:
            messages.error(request, "Você não pode adicionar a si mesmo.")
            return redirect('amizades:adicionar')

        try:
            para = User.objects.get(username=target_username)
        except User.DoesNotExist:
            messages.error(request, f"Usuário '{target_username}' não encontrado.")
            return redirect('amizades:adicionar')

        # Verifica se já são amigos:
        u1, u2 = (request.user, para) if request.user.id < para.id else (para, request.user)
        if Amizade.objects.filter(usuario1=u1, usuario2=u2).exists():
            messages.info(request, f"Vocês já são amigos de '{target_username}'.")
            return redirect('amizades:adicionar')

        # Verifica se já existe pedido pendente:
        pendente = PedidoAmizade.objects.filter(de_usuario=request.user, para_usuario=para).exists()
        recebido = PedidoAmizade.objects.filter(de_usuario=para, para_usuario=request.user).exists()
        if pendente:
            messages.warning(request, f"Você já enviou um pedido para '{target_username}'.")
        elif recebido:
            # Se o outro já enviou pedido, aceita automaticamente
            pedido = PedidoAmizade.objects.get(de_usuario=para, para_usuario=request.user)
            pedido.aceito = True
            pedido.save()
            Amizade.criar_amizade_mutua(request.user, para)
            messages.success(request, f"Pedido de '{target_username}' aceito automaticamente! Agora são amigos.")
        else:
            # Cria novo pedido
            PedidoAmizade.objects.create(de_usuario=request.user, para_usuario=para)
            messages.success(request, f"Pedido enviado para '{target_username}'. Aguardando aceitação.")
        return redirect('amizades:adicionar')

    # ----------------------------------------------------------------
    # 2) Se for GET, faz a busca e constrói friend_ids
    # ----------------------------------------------------------------
    query = request.GET.get('username', '').strip()
    results = []
    if query:
        # Busca todos os usuários cujo username contenha ‘query’, exceto o próprio
        results = User.objects.filter(username__icontains=query).exclude(id=request.user.id)

    # Monta um set de IDs de amigos
    friend_ids = set()
    # Buscando amizades onde request.user aparece como usuario1 ou usuario2
    amizades = Amizade.objects.filter(
        Q(usuario1=request.user) | Q(usuario2=request.user)
    )
    for amizade in amizades:
        if amizade.usuario1 == request.user:
            friend_ids.add(amizade.usuario2_id)
        else:
            friend_ids.add(amizade.usuario1_id)

    return render(request, 'amizades/adicionar.html', {
        'results': results,
        'query': query,
        'friend_ids': friend_ids
    })


@login_required
def lista_pedidos_entrada(request):
    """
    Lista todos os pedidos recebidos por request.user que ainda não foram aceitos/rejeitados.
    """
    pedidos = PedidoAmizade.objects.filter(para_usuario=request.user, aceito=False)
    return render(request, 'amizades/pedidos_recebidos.html', {'pedidos': pedidos})


@login_required
def aceitar_pedido(request, pedido_id):
    pedido = get_object_or_404(PedidoAmizade, id=pedido_id, para_usuario=request.user)
    if not pedido.aceito:
        pedido.aceito = True
        pedido.save()
        # Cria amizade mútua
        Amizade.criar_amizade_mutua(request.user, pedido.de_usuario)
        messages.success(request, f"Você aceitou o pedido de '{pedido.de_usuario.username}'.")
    return redirect('amizades:pedidos_entrada')


@login_required
def recusar_pedido(request, pedido_id):
    pedido = get_object_or_404(PedidoAmizade, id=pedido_id, para_usuario=request.user)
    pedido.delete()
    messages.info(request, f"Você recusou o pedido de '{pedido.de_usuario.username}'.")
    return redirect('amizades:pedidos_entrada')


@login_required
def lista_amigos(request):
    """
    Exibe a lista de amigos de request.user.
    Como gravamos a amizade em (usuario1,usuario2) com id menor primeiro,
    precisamos verificar ambas as colunas.
    """
    from django.db.models import Q

    # Todos os objetos Amizade onde user é usuario1 ou usuario2:
    amizades = Amizade.objects.filter(
        Q(usuario1=request.user) | Q(usuario2=request.user)
    )

    # Construímos lista de usuários “amigos” (excluindo ele mesmo).
    amigos = []
    for a in amizades:
        if a.usuario1 == request.user:
            amigos.append(a.usuario2)
        else:
            amigos.append(a.usuario1)

    return render(request, 'amizades/lista_amigos.html', {'amigos': amigos})


User = get_user_model()


@login_required
def meus_alunos(request):
    # Somente Personal Trainers acessam esta página
    if not hasattr(request.user, 'profile') or not request.user.profile.is_personal:
        return render(request, 'amizades/meus_alunos.html')

    # 1) Montar lista de “amigos” (outros usuários com quem existe Amizade)
    amizades_qs = Amizade.objects.filter(
        Q(usuario1=request.user) | Q(usuario2=request.user)
    )
    amigos = []
    for amizade in amizades_qs:
        if amizade.usuario1 == request.user:
            amigos.append(amizade.usuario2)
        else:
            amigos.append(amizade.usuario1)

    # 2) Alunos já aceitos (ManyToManyField students no Profile)
    alunos = request.user.profile.students.all()

    # 3) IDs de convites pendentes enviados por este Personal
    pendentes_qs = PersonalInvite.objects.filter(
        personal=request.user,
        aceito=False
    ).values_list('para_usuario_id', flat=True)
    pendentes_ids = set(pendentes_qs)

    return render(request, 'amizades/meus_alunos.html', {
        'amigos': amigos,
        'alunos': alunos,
        'pendentes_ids': pendentes_ids,
    })


@login_required
def enviar_convite_aluno(request, amigo_id):
    # Só Personal Trainer pode enviar convite
    if not hasattr(request.user, 'profile') or not request.user.profile.is_personal:
        return redirect('amizades:meus_alunos')

    amigo = get_object_or_404(User, pk=amigo_id)

    # Verificar se são amigos antes de enviar
    existe = Amizade.objects.filter(
        Q(usuario1=request.user, usuario2=amigo) |
        Q(usuario1=amigo,   usuario2=request.user)
    ).exists()
    if not existe:
        messages.error(request, "Você só pode convidar quem é seu amigo.")
        return redirect('amizades:meus_alunos')

    # Apaga convites antigos (para poder reenviar após remoção)
    PersonalInvite.objects.filter(personal=request.user, para_usuario=amigo).delete()

    # Cria um novo convite
    PersonalInvite.objects.create(personal=request.user, para_usuario=amigo)
    messages.success(request, f"Convite enviado para {amigo.get_full_name() or amigo.username}.")
    return redirect('amizades:meus_alunos')


@login_required
def aceitar_convite(request, pk):
    convite = get_object_or_404(
        PersonalInvite,
        pk=pk,
        para_usuario=request.user,
        aceito=False
    )
    convite.aceito = True
    convite.save()
    # adiciona o aluno no Profile do personal
    convite.personal.profile.students.add(request.user)
    messages.success(request, f"Você agora é aluno de {convite.personal.username}.")
    return redirect('amizades:meus_personals')



@login_required
def remover_aluno(request, user_id):
    profile = request.user.profile
    aluno = get_object_or_404(User, pk=user_id)
    profile.students.remove(aluno)
    messages.success(
        request,
        f"{aluno.get_full_name() or aluno.username} foi removido dos seus alunos."
    )
    # redireciona de volta à aba correta
    if hasattr(request.user, 'profile') and request.user.profile.is_personal:
        return redirect('amizades:meus_alunos')
    else:
        return redirect('amizades:meus_personals')

@login_required
def meus_personals(request):
    # 1) Convida apenas se este usuário NÃO for Personal
    if hasattr(request.user, 'profile') and request.user.profile.is_personal:
        # Se for Personal, não tem sentido ver “meus_personals” (é um Personal).
        # Você pode redirecionar ou exibir mensagem simples:
        return render(request, 'amizades/meus_personals.html', {
            'is_personal': True
        })

    # 2) Convites pendentes enviados a este usuário (i.e. este usuário é “para_usuario”)
    convites_recebidos = PersonalInvite.objects.filter(
        para_usuario=request.user,
        aceito=False
    ).select_related('personal__profile')

    # 3) Todos os Personals que aceitaram este aluno → 
    #    “request.user.personals” retorna todos os Profile cujo M2M students inclui este user.
    perfis_personals = request.user.personals.all()  # Queryset de Profile
    personals_users = [p.user for p in perfis_personals]  # converte pra lista de User

    return render(request, 'amizades/meus_personals.html', {
        'convites_recebidos': convites_recebidos,
        'personals': personals_users,
        'is_personal': False,
    })
