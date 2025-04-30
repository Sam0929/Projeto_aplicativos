from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import TreinoForm
from .models import Treino, GrupoMuscular, Exercicio, ExecucaoTreino, ExecucaoExercicio
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Max
from collections import Counter, defaultdict
from django.db.models import Prefetch
from django.shortcuts import render

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
    # 1) Busque todas as execuções do usuário
    execucoes = ExecucaoTreino.objects.filter(
        usuario=request.user
    ).select_related('treino').order_by('-data_inicio')

    # 2) Pré-calcule estatísticas de moda e máxima para cada treino+exercício
    #    Estrutura: { treino_id: { exercicio_id: {'moda':.., 'maxima':..}, ... }, ... }
    global_stats = {}
    treino_ids = {e.treino_id for e in execucoes}
    for tid in treino_ids:
        itens_hist = ExecucaoExercicio.objects.filter(
            execucao_treino__treino_id=tid
        )
        cargas_por_ex = defaultdict(list)
        for ih in itens_hist:
            cargas_por_ex[ih.exercicio_id].append(ih.carga_utilizada)

        stats = {}
        for eid, cargas in cargas_por_ex.items():
            stats[eid] = {
                'moda': Counter(cargas).most_common(1)[0][0],
                'maxima': max(cargas),
            }
        global_stats[tid] = stats

    # 3) Para cada execução, monte os detalhes agrupados por exercício
    for execucao in execucoes:
        stats = global_stats.get(execucao.treino_id, {})
        itens_exec = ExecucaoExercicio.objects.filter(
            execucao_treino=execucao
        ).select_related('exercicio')

        # agrupa cargas desta execução por exercício
        usadas_por_ex = defaultdict(list)
        for item in itens_exec:
            usadas_por_ex[item.exercicio].append(item.carga_utilizada)

        detalhes = []
        perf_indices = []
        for ex_obj, cargas_usadas in usadas_por_ex.items():
            hist = stats.get(ex_obj.id, {'moda': 0, 'maxima': 0})
            carga_moda  = hist['moda']
            carga_max   = hist['maxima']

            # índice de desempenho (cada série / máximo histórico)
            for carga in cargas_usadas:
                if carga_max > 0:
                    perf_indices.append(carga / carga_max)

            detalhes.append({
                'exercicio':        ex_obj.nome,
                'cargas_usadas':    cargas_usadas,
                'carga_mais_usada': carga_moda,
                'carga_maxima':     carga_max,
            })

        # calcula desempenho geral (você já tinha isso)
        pct = sum(perf_indices) / len(perf_indices) if perf_indices else 0
        if pct >= 0.9:
            execucao.desempenho = 'Ótimo'
        elif pct >= 0.7:
            execucao.desempenho = 'Bom'
        elif pct >= 0.5:
            execucao.desempenho = 'Regular'
        else:
            execucao.desempenho = 'Ruim'

        execucao.detalhes = detalhes

    return render(request, 'treinos/historico_treino.html', {
        'execucoes': execucoes
    })




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
    return render(request, 'users/home.html', {'treino': treino})


@login_required
def iniciar_treino(request, treino_id):
    treino = get_object_or_404(Treino, id=treino_id, usuario=request.user)

    # Prepara os grupos e exercícios (com séries e dados históricos)
    grupos_qs = treino.grupomuscular_set.prefetch_related('exercicio_set')
    execution_groups = []
    for grupo in grupos_qs:
        ex_list = []
        for ex in grupo.exercicio_set.all():
            # séries
            ex.series_range = range(1, ex.series + 1)

            # histórico daquele exercício neste treino
            hist = ExecucaoExercicio.objects.filter(
                execucao_treino__treino=treino,
                exercicio=ex
            )
            # último peso
            last = hist.order_by('-execucao_treino__data_inicio', '-serie').first()
            ex.last_weight = last.carga_utilizada if last else None
            # peso máximo
            agg = hist.aggregate(m=Max('carga_utilizada'))
            ex.max_weight = agg['m'] if agg['m'] is not None else None

            ex_list.append(ex)
        execution_groups.append({
            'grupo': grupo,
            'exercicios': ex_list
        })

    if request.method == 'POST':
        execucao = ExecucaoTreino.objects.create(
            treino=treino, usuario=request.user
        )

        soma_carga   = 0.0
        soma_tempo   = timedelta()
        contador_ser = 0

        for key, val in request.POST.items():
            if not key.startswith("peso_"):
                continue
            _, ex_id, serie = key.split("_")
            carga = float(val) if val else 0.0
            dur_sec = int(request.POST.get(f"duracao_{ex_id}_{serie}", 0))
            duracao = timedelta(seconds=dur_sec)

            ExecucaoExercicio.objects.create(
                execucao_treino=execucao,
                exercicio_id=int(ex_id),
                serie=int(serie),
                carga_utilizada=carga,
                duracao=duracao,
            )

            soma_carga   += carga
            soma_tempo   += duracao
            contador_ser += 1

        execucao.carga_total = (soma_carga / contador_ser) if contador_ser else 0.0
        execucao.duracao     = soma_tempo
        execucao.save()

        return redirect('treinos:historico_treino')

    return render(request, 'treinos/iniciar_treino.html', {
        'treino': treino,
        'execution_groups': execution_groups
    })