from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Treino

@login_required
def lista_treinos(request):
    treinos = Treino.objects.filter(usuario=request.user)
    return render(request, 'treinos/lista_treinos.html', {'treinos': treinos})

@login_required
def novo_treino(request):
    if request.method == 'POST':
        nome = request.POST['nome']
        descricao = request.POST.get('descricao', '')
        Treino.objects.create(nome=nome, descricao=descricao, usuario=request.user)
        return redirect('treinos:lista_treinos')
    return render(request, 'treinos/novo_treino.html')

@login_required
def detalhe_treino(request, pk):
    treino = get_object_or_404(Treino, pk=pk, usuario=request.user)
    return render(request, 'treinos/detalhe_treino.html', {'treino': treino})

@login_required
def historico_treino(request):
    treinos = Treino.objects.filter(usuario=request.user).order_by('-criado_em')
    return render(request, 'treinos/historico_treino.html', {'treinos': treinos})