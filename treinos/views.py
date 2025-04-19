from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Treino

@login_required
def lista_treinos(request):
    treinos = Treino.objects.filter(usuario=request.user).prefetch_related('grupomuscular_set')
    return render(request, 'treinos/lista_treinos.html', {'treinos': treinos})

@login_required
def detalhe_treino(request, pk):
    treino = get_object_or_404(
        Treino.objects.prefetch_related('grupomuscular_set__exercicio_set'), 
        pk=pk, 
        usuario=request.user
    )
    return render(request, 'treinos/detalhe_treino.html', {'treino': treino})



@login_required
def historico_treino(request):
    treinos = Treino.objects.filter(usuario=request.user).order_by('-criado_em')
    return render(request, 'treinos/historico_treino.html', {'treinos': treinos})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Treino, GrupoMuscular, Exercicio
from .forms import TreinoForm

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Treino, GrupoMuscular, Exercicio
from .forms import TreinoForm

@login_required
def novo_treino(request):
    if request.method == 'POST':
        form = TreinoForm(request.POST)
        if form.is_valid():
            # 1) Cria o Treino
            treino = Treino.objects.create(
                nome=form.cleaned_data['nome_treino'],
                usuario=request.user
            )

            # 2) Para cada grupo...
            grupos = request.POST.getlist('grupos[]')
            for g_idx, nome_grupo in enumerate(grupos):
                grupo = GrupoMuscular.objects.create(
                    treino=treino,
                    nome=nome_grupo
                )

                # 3) Pega listas de exercícios COM O MESMO ÍNDICE DO GRUPO
                nomes      = request.POST.getlist(f'exercicios[{g_idx}][nome]')
                series     = request.POST.getlist(f'exercicios[{g_idx}][series]')    # <– corrigido
                reps       = request.POST.getlist(f'exercicios[{g_idx}][reps]')
                descansos  = request.POST.getlist(f'exercicios[{g_idx}][descanso]')

                # 4) Cria cada Exercicio
                for nome, s, r, d in zip(nomes, series, reps, descansos):
                    Exercicio.objects.create(
                        grupo=grupo,
                        nome=nome,
                        series=int(s),
                        repeticoes=int(r),
                        descanso=int(d)
                    )

            return redirect('treinos:lista_treinos')
    else:
        form = TreinoForm()

    return render(request, 'treinos/novo_treino.html', {
        'form': form
    })


@login_required
def editar_treino(request, pk):
    treino = get_object_or_404(Treino, pk=pk, usuario=request.user)
    
    if request.method == 'POST':
        # Atualiza nome do treino
        treino.nome = request.POST['nome_treino']
        treino.save()

        # Remove todos os grupos/exercícios existentes
        treino.grupomuscular_set.all().delete()

        # Recria estrutura com novos dados
        grupos = request.POST.getlist('grupos[]')
        for grupo_index, grupo_nome in enumerate(grupos):
            grupo = GrupoMuscular.objects.create(
                treino=treino,
                nome=grupo_nome
            )

            exercicios_nomes = request.POST.getlist(f'exercicios[{grupo_index}][nome]')
            exercicios_series = request.POST.getlist(f'exercicios[{grupo_index}][series]')
            exercicios_reps = request.POST.getlist(f'exercicios[{grupo_index}][reps]')
            exercicios_descanso = request.POST.getlist(f'exercicios[{grupo_index}][descanso]')

            for nome, series, descanso, reps in zip(exercicios_nomes, exercicios_series, exercicios_descanso, exercicios_reps):
                Exercicio.objects.create(
                    grupo=grupo,
                    nome=nome,
                    series=series,
                    descanso=descanso,
                    repeticoes=reps
                )

        return redirect('treinos:detalhe_treino', pk=treino.pk)

    return render(request, 'treinos/editar_treino.html', {'treino': treino})

@login_required
def excluir_treino(request, pk):
    treino = get_object_or_404(Treino, pk=pk, usuario=request.user)
    if request.method == 'POST':
        treino.delete()
        return redirect('treinos:lista_treinos')
    return render(request, 'treinos/confirmar_exclusao.html', {'treino': treino})

@login_required
def iniciar_treino(request, pk):
    # carrega o treino (só pra garantir que pertence ao usuário)
    treino = get_object_or_404(Treino, pk=pk, usuario=request.user)
    # por enquanto, não muda nada — só salva para "registrar" execução
    treino.save()
    # redireciona de volta pro detalhe
    return redirect('treinos:detalhe_treino', pk=pk)