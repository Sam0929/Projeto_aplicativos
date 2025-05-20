from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import TreinoForm
from .models import Treino, GrupoMuscular, Exercicio, ExecucaoTreino, ExecucaoExercicio
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Max, Prefetch
from collections import Counter, defaultdict
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Treino, CompartilhamentoTreino
from amizades.models import Amizade
from itertools import chain
from django.http import Http404


@login_required
def lista_treinos(request):
    treinos_proprios = Treino.objects.filter(usuario=request.user).prefetch_related('grupomuscular_set')
    treinos_recebidos = Treino.objects.filter(
        compartilhamentos__para_usuario=request.user
    ).prefetch_related('grupomuscular_set').distinct()
    from itertools import chain
    treinos = list(chain(treinos_proprios, treinos_recebidos))
    return render(request, 'treinos/lista_treinos.html', {'treinos': treinos})


@login_required
def detalhe_treino(request, pk):
    """
    Se o treino for do próprio usuário, carrega normalmente.
    Se não, verifica se existe CompartilhamentoTreino para este usuário.
    Caso contrário, lança 404.
    """
    # 1. Tenta buscar o treino como sendo do próprio usuário
    try:
        treino = Treino.objects.prefetch_related(
            'grupomuscular_set__exercicio_set'
        ).get(pk=pk, usuario=request.user)
        acesso_proprio = True
    except Treino.DoesNotExist:
        # 2. Se não encontrou, verifica se foi compartilhado com o usuário
        treino = get_object_or_404(
            Treino.objects.prefetch_related('grupomuscular_set__exercicio_set'),
            pk=pk
        )
        acesso_proprio = False
        # Verifica se existe um compartilhamento para este treino e para este usuário
        tem_acesso = CompartilhamentoTreino.objects.filter(
            treino=treino,
            para_usuario=request.user
        ).exists()
        if not tem_acesso:
            raise Http404("Você não tem permissão para ver este treino.")

    return render(request, 'treinos/detalhe_treino.html', {
        'treino': treino,
        'acesso_proprio': acesso_proprio
    })




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

def treinos_visiveis_para(usuario):
    treinos_proprios = Treino.objects.filter(usuario=usuario)
    treinos_compartilhados = Treino.objects.filter(
        compartilhamentos__para_usuario=usuario
    ).exclude(usuario=usuario)  

    return treinos_proprios.union(treinos_compartilhados)




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
    """
    Permite iniciar e gravar execução somente para treino próprio ou compartilhado.
    Ajusta o histórico (last_weight e max_weight) para levar em conta
    apenas este usuário (request.user), não o dono original do treino.
    """
    # 1) Verifica acesso (dono ou compartilhado)
    try:
        treino = Treino.objects.prefetch_related('grupomuscular_set__exercicio_set') \
                               .get(id=treino_id, usuario=request.user)
        acesso_proprio = True
    except Treino.DoesNotExist:
        treino = get_object_or_404(
            Treino.objects.prefetch_related('grupomuscular_set__exercicio_set'),
            id=treino_id
        )
        acesso_proprio = False
        if not CompartilhamentoTreino.objects.filter(
            treino=treino, para_usuario=request.user
        ).exists():
            raise Http404("Você não tem permissão para ver este treino.")

    # 2) Monta os grupos e exercícios, já incluindo histórico filtrado por request.user
    grupos_qs = treino.grupomuscular_set.prefetch_related('exercicio_set')
    execution_groups = []
    for grupo in grupos_qs:
        ex_list = []
        for ex in grupo.exercicio_set.all():
            # Séries
            ex.series_range = range(1, ex.series + 1)

            # Histórico deste exercício, mas **apenas** para este usuário
            hist = ExecucaoExercicio.objects.filter(
                execucao_treino__treino=treino,
                execucao_treino__usuario=request.user,  # <— somente executado por quem está rodando agora
                exercicio=ex
            )

            # Último peso que ESTE usuário utilizou neste exercício  
            last = hist.order_by('-execucao_treino__data_inicio', '-serie').first()
            ex.last_weight = last.carga_utilizada if last else None

            # Peso máximo que ESTE usuário atingiu neste exercício  
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

        soma_carga = 0.0
        soma_tempo = timedelta()
        contador_ser = 0

        # Grava cargas e durações usando o único campo duracao_exercicio_<ex.id>
        for key, val in request.POST.items():
            if not key.startswith("peso_"):
                continue

            _, ex_id, serie = key.split("_")
            carga = float(val) if val else 0.0

            dur_sec = int(request.POST.get(f"duracao_exercicio_{ex_id}", 0))
            duracao = timedelta(seconds=dur_sec)

            ExecucaoExercicio.objects.create(
                execucao_treino=execucao,
                exercicio_id=int(ex_id),
                serie=int(serie),
                carga_utilizada=carga,
                duracao=duracao,
            )

            soma_carga += carga
            soma_tempo += duracao
            contador_ser += 1

        execucao.carga_total = (soma_carga / contador_ser) if contador_ser else 0.0
        execucao.duracao = soma_tempo
        execucao.save()

        return redirect('treinos:historico_treino')

    return render(request, 'treinos/iniciar_treino.html', {
        'treino': treino,
        'execution_groups': execution_groups,
        'acesso_proprio': acesso_proprio
    })

    



User = get_user_model()

@login_required
def compartilhar_treino(request, treino_id):
    treino = get_object_or_404(Treino, id=treino_id)

    if request.method == 'POST':
        
        amigos_ids = request.POST.getlist('amigos')
        for amigo_id in amigos_ids:
            amigo = get_object_or_404(User, id=amigo_id)
            
            CompartilhamentoTreino.objects.get_or_create(
                treino=treino,
                de_usuario=request.user,
                para_usuario=amigo
            )
        return redirect('treinos:lista_treinos')

    
    amizades_qs = Amizade.objects.filter(
        Q(usuario1=request.user) | Q(usuario2=request.user)
    )
    amigos = []
    for a in amizades_qs:
        if a.usuario1 == request.user:
            amigos.append(a.usuario2)
        else:
            amigos.append(a.usuario1)

    return render(request, 'treinos/compartilhar_treino.html', {
        'treino': treino,
        'amigos': amigos
    })