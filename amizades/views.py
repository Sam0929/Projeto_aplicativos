from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

from .models import PedidoAmizade, Amizade

User = get_user_model()

@login_required
def adicionar_ou_enviar_pedido(request):
    """
    Página onde o usuário digita um username para enviar pedido de amizade.
    Se usuário válido e sem pedido existente, cria PedidoAmizade.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        if username == request.user.username:
            messages.error(request, "Você não pode adicionar a si mesmo.")
            return redirect('amizades:adicionar')

        try:
            para = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, f"Usuário '{username}' não encontrado.")
            return redirect('amizades:adicionar')

        # Verifica se já são amigos:
        u1, u2 = (request.user, para) if request.user.id < para.id else (para, request.user)
        if Amizade.objects.filter(usuario1=u1, usuario2=u2).exists():
            messages.info(request, f"Vocês já são amigos de {username}.")
            return redirect('amizades:adicionar')

        # Verifica se já existe pedido pendente
        pendente = PedidoAmizade.objects.filter(de_usuario=request.user, para_usuario=para).exists()
        recebido = PedidoAmizade.objects.filter(de_usuario=para, para_usuario=request.user).exists()
        if pendente:
            messages.warning(request, f"Você já enviou um pedido para '{username}'.")
        elif recebido:
            # Se para->request.user já enviou pedido, então aceitarmos diretamente:
            pedido = PedidoAmizade.objects.get(de_usuario=para, para_usuario=request.user)
            pedido.aceito = True
            pedido.save()
            # Cria amizade mútua:
            Amizade.criar_amizade_mutua(request.user, para)
            messages.success(request, f"Pedido de '{username}' aceito automaticamente! Agora são amigos.")
        else:
            # Cria pedido novo
            PedidoAmizade.objects.create(de_usuario=request.user, para_usuario=para)
            messages.success(request, f"Pedido enviado para '{username}'. Aguardando aceitação.")
        return redirect('amizades:adicionar')

    return render(request, 'amizades/adicionar.html')


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

