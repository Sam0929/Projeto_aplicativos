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
    Exibe detalhes de um treino:
    - Se for do próprio usuário -> acesso_proprio = True
    - Se não for, verifica se existe CompartilhamentoTreino para este usuário.
      Caso exista, mostra “🔗 Compartilhado por …”, caso contrário, permite visualizar normalmente.
    """

    # 1) Busca o treino sem filtrar por usuário, só pelo ID
    treino = get_object_or_404(
        Treino.objects.prefetch_related('grupomuscular_set__exercicio_set', 'usuario'),
        pk=pk
    )

    # 2) Verifica se é acesso do próprio dono
    acesso_proprio = (treino.usuario == request.user)

    # 3) Se não for o próprio dono, tenta obter o compartilhamento
    compartilhamento = None
    if not acesso_proprio:
        compartilhamento = CompartilhamentoTreino.objects.filter(
            treino=treino,
            para_usuario=request.user
        ).first()
        # Observação: não lançamos 404 se não tiver compartilhamento,
        # pois agora qualquer um pode ver o treino. Apenas exibiremos se veio compartilhado.

    return render(request, 'treinos/detalhe_treino.html', {
        'treino': treino,
        'acesso_proprio': acesso_proprio,
        'compartilhamento': compartilhamento,
    })


@login_required
def historico_treino(request):
    # 1) Busque todas as execuções do usuário
    execucoes = (
        ExecucaoTreino.objects
        .filter(usuario=request.user)
        .select_related('treino')
        .order_by('-data_inicio')
    )

    # 2) Pré-calcule estatísticas de moda e máxima para cada treino+exercício
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

    execucoes_data = []
    for execucao in execucoes:
        stats_do_treino = global_stats.get(execucao.treino_id, {})
        perf_indices = []
        grupos_data = []

        # Para cada grupo muscular
        for grupo in execucao.treino.grupomuscular_set.all().prefetch_related('exercicio_set'):
            exercicios_data = []

            for ex in grupo.exercicio_set.all():
                # Obter todas as ExecucaoExercicio desta execução e exercício
                series_exec = ExecucaoExercicio.objects.filter(
                    execucao_treino=execucao,
                    exercicio=ex
                )

                # Lista de pesos de cada série (para exibir)
                series_weights = [ce.carga_utilizada for ce in series_exec.order_by('serie')]

                # Agora, para duração do exercício, pegamos o máximo de `duracao` (pois apenas a 1ª série
                # tinha o tempo total do exercício; demais tinham zero)
                duracao_total_ex = series_exec.aggregate(max_dur=Max('duracao'))['max_dur'] or 0

                # Estatísticas históricas
                hist = stats_do_treino.get(ex.id, {'moda': 0, 'maxima': 0})
                carga_moda = hist['moda']
                carga_max = hist['maxima']

                # Índice de desempenho: cada série / carga_max
                for ce in series_exec:
                    if carga_max > 0:
                        perf_indices.append(ce.carga_utilizada / carga_max)

                exercicios_data.append({
                    'nome_ex': ex.nome,
                    'series_weights': series_weights,
                    'duracao_total_ex': duracao_total_ex,
                    'carga_moda': carga_moda,
                    'carga_max': carga_max,
                })

            if exercicios_data:
                grupos_data.append({
                    'nome_grupo': grupo.nome,
                    'exercicios': exercicios_data
                })

        # 4) Cálculo do desempenho geral
        pct = sum(perf_indices) / len(perf_indices) if perf_indices else 0
        if pct >= 0.9:
            desempenho = 'Ótimo'
        elif pct >= 0.7:
            desempenho = 'Bom'
        elif pct >= 0.5:
            desempenho = 'Regular'
        else:
            desempenho = 'Ruim'

        # 5) Duração total em minutos da execução (soma das durações dos exercícios)
        duracao_total_seg = execucao.duracao.total_seconds()
        duracao_minutos = int(duracao_total_seg // 60)

        execucoes_data.append({
            'id': execucao.id,
            'nome_treino': execucao.treino.nome,
            'data_inicio': execucao.data_inicio,
            'duracao_minutos': duracao_minutos,
            'desempenho': desempenho,
            'detalhes': grupos_data,
        })

    return render(request, 'treinos/historico_treino.html', {
        'execucoes_data': execucoes_data
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

    # 1) Verifica acesso: tenta buscar como treino próprio; se não, verifica compartilhamento
    try:
        treino = Treino.objects.prefetch_related(
            'grupomuscular_set__exercicio_set'
        ).get(id=treino_id, usuario=request.user)
        acesso_proprio = True
        compartilhamento = None
    except Treino.DoesNotExist:
        # não é treino próprio, busca sem filtrar por usuário
        treino = get_object_or_404(
            Treino.objects.prefetch_related('grupomuscular_set__exercicio_set'),
            id=treino_id
        )
        acesso_proprio = False
        # checa se esse treino foi compartilhado com request.user
        compartilhamento = CompartilhamentoTreino.objects.filter(
            treino=treino,
            para_usuario=request.user
        ).first()
        if not compartilhamento:
            # nem é do próprio, nem está compartilhado -> 404
            raise Http404("Você não tem permissão para iniciar este treino.")

    # 2) Monta os grupos e exercícios, já incluindo histórico filtrado por request.user
    grupos_qs = treino.grupomuscular_set.prefetch_related('exercicio_set')
    execution_groups = []
    for grupo in grupos_qs:
        ex_list = []
        for ex in grupo.exercicio_set.all():
            # Séries
            ex.series_range = range(1, ex.series + 1)

            # Histórico deste exercício, mas apenas para este usuário:
            hist = ExecucaoExercicio.objects.filter(
                execucao_treino__treino=treino,
                execucao_treino__usuario=request.user,
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

    # 3) Se for POST, grava a execução: cada série e a duração total apenas na 1ª série de cada exercício
    if request.method == 'POST':
        execucao = ExecucaoTreino.objects.create(
            treino=treino,
            usuario=request.user
        )

        # Primeiro, coleta as durações totais passadas no form: "duracao_exercicio_<ex_id>"
        duracoes_por_ex = {}
        for key, val in request.POST.items():
            if not key.startswith("duracao_exercicio_"):
                continue
            parts = key.split("_")
            # esperamos ["duracao", "exercicio", "<ex_id>"]
            if len(parts) == 3:
                try:
                    ex_id = int(parts[2])
                    dur_sec = int(val) if val else 0
                except ValueError:
                    ex_id = None
                    dur_sec = 0
                if ex_id is not None:
                    duracoes_por_ex[ex_id] = dur_sec

        soma_carga = 0.0
        soma_tempo = timedelta()
        contador_ser = 0

        # Para cada campo "peso_<ex_id>_<serie>"
        series_contagem = defaultdict(int)  # conta quantas séries já gravamos por ex_id
        for key, val in request.POST.items():
            if not key.startswith("peso_"):
                continue
            # key == "peso_<ex_id>_<serie>"
            try:
                _, ex_id_str, serie_str = key.split("_")
                ex_id = int(ex_id_str)
                serie_num = int(serie_str)
                carga = float(val) if val else 0.0
            except (ValueError, TypeError):
                # caso o form tenha algo inválido, pula
                continue

            # Se for a primeira série deste exercício, usamos a duração total; senão, zero
            dur_totais_seg = duracoes_por_ex.get(ex_id, 0)
            if series_contagem[ex_id] == 0:
                duracao = timedelta(seconds=dur_totais_seg)
            else:
                duracao = timedelta(seconds=0)

            # Cria o registro ExecucaoExercicio
            ExecucaoExercicio.objects.create(
                execucao_treino=execucao,
                exercicio_id=ex_id,
                serie=serie_num,
                carga_utilizada=carga,
                duracao=duracao,
            )

            series_contagem[ex_id] += 1
            soma_carga += carga
            soma_tempo += duracao
            contador_ser += 1

        execucao.carga_total = (soma_carga / contador_ser) if contador_ser else 0.0
        execucao.duracao = soma_tempo
        execucao.save()

        return redirect('treinos:historico_treino')

    # 4) GET: renderiza o template normalmente
    return render(request, 'treinos/iniciar_treino.html', {
        'treino': treino,
        'execution_groups': execution_groups,
        'acesso_proprio': acesso_proprio,
        'compartilhamento': compartilhamento,
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
    
@login_required
def adicionar_treino(request, pk):
    """
    Clona o treino (com todos os grupos e exercícios) para o usuário logado,
    renomeando o novo como “<nome original> (Cópia)”.
    """
    treino_original = get_object_or_404(
        Treino.objects.prefetch_related('grupomuscular_set__exercicio_set'),
        pk=pk
    )

    if request.method == 'POST':
        # 1) Cria o novo treino para o request.user
        novo_treino = Treino.objects.create(
            nome=f"{treino_original.nome} (Cópia)",
            usuario=request.user
        )
        # 2) Copia todos os grupos e exercícios
        for grupo in treino_original.grupomuscular_set.all():
            novo_grupo = GrupoMuscular.objects.create(
                nome=grupo.nome,
                treino=novo_treino
            )
            for exercicio in grupo.exercicio_set.all():
                Exercicio.objects.create(
                    nome=exercicio.nome,
                    series=exercicio.series,
                    repeticoes=exercicio.repeticoes,
                    descanso=exercicio.descanso,
                    carga_maxima=exercicio.carga_maxima,
                    grupo=novo_grupo
                )
        # 3) Redireciona para a página de detalhes do novo treino
        return redirect('treinos:detalhe_treino', pk=novo_treino.pk)

    # Se o método não for POST, redireciona de volta ao detalhe original
    return redirect('treinos:detalhe_treino', pk=treino_original.pk)