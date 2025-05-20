from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import PedidoAmizade, Amizade
from django.db.models import Q



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

