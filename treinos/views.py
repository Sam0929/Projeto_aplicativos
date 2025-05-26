from django.contrib import messages 
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
import base64
from io import BytesIO
import matplotlib.pyplot as plt
from datetime import timedelta, date
from django.utils import timezone
from django.db.models import Count


User = get_user_model()


@login_required
def lista_treinos(request):
    """
    Lista apenas os treinos próprios + compartilhados que já foram aceitos.
    Permite filtrar por nome via GET['q'].
    """
    q = request.GET.get('q', '').strip()
    # Treinos próprios
    qs_proprios = Treino.objects.filter(usuario=request.user)
    # Treinos compartilhados com este usuário e aceitos
    qs_compartilhados = Treino.objects.filter(
        compartilhamentos__para_usuario=request.user,
        compartilhamentos__aceito=True
    )

    if q:
        qs_proprios = qs_proprios.filter(nome__icontains=q)
        qs_compartilhados = qs_compartilhados.filter(nome__icontains=q)

    treinos_proprios = qs_proprios.prefetch_related('grupomuscular_set')
    treinos_compartilhados = qs_compartilhados.prefetch_related('grupomuscular_set')

    # Mesclamos em uma lista, indicando “compartilhado” para os segundos
    treinos = list(treinos_proprios) + list(treinos_compartilhados)

    return render(request, 'treinos/lista_treinos.html', {
        'treinos': treinos,
        'q': q,
    })


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

        # Destinado a cada grupo muscular
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

    # 1) Recupera todos os amigos do request.user:
    amizades_qs = Amizade.objects.filter(
        Q(usuario1=request.user) | Q(usuario2=request.user)
    )
    amigos = []
    for a in amizades_qs:
        if a.usuario1 == request.user:
            amigos.append(a.usuario2)
        else:
            amigos.append(a.usuario1)

    # 2) Monta uma lista de dicionários: para cada amigo, definimos se "já possui" o treino ou não
    amigos_status = []
    for amigo in amigos:
        # Verifica se 'amigo' é o dono do treino
        ja_dono = (treino.usuario_id == amigo.id)

        # Verifica se já há um CompartilhamentoTreino (pendente ou aceito) para esse amigo e treino
        existe_compart = CompartilhamentoTreino.objects.filter(
            treino=treino,
            para_usuario=amigo
        ).exists()

        ja_possui = ja_dono or existe_compart

        amigos_status.append({
            'user': amigo,
            'ja_possui': ja_possui
        })

    if request.method == 'POST':
        # Faz loop pelos checkboxes enviados
        ids_selecionados = request.POST.getlist('amigos')
        for amigo_id in ids_selecionados:
            try:
                amigo = User.objects.get(id=amigo_id)
            except User.DoesNotExist:
                continue

            # Se já possui, ignoramos
            if CompartilhamentoTreino.objects.filter(treino=treino, para_usuario=amigo).exists():
                continue

            # Cria novo pedido de compartilhamento
            CompartilhamentoTreino.objects.create(
                treino=treino,
                de_usuario=request.user,
                para_usuario=amigo
            )
        messages.success(request, f"Pedidos de compartilhamento enviados com sucesso!")
        return redirect('treinos:lista_treinos')

    return render(request, 'treinos/compartilhar_treino.html', {
        'treino': treino,
        'amigos_status': amigos_status
    })



@login_required
def lista_pedidos_compartilhamento(request):
    """
    Mostra todos os compartilhamentos pendentes para o usuário atual,
    ou seja, registros CompartilhamentoTreino.aceito==False e para_usuario=request.user.
    """
    pedidos = CompartilhamentoTreino.objects.filter(
        para_usuario=request.user,
        aceito=False
    ).select_related('treino', 'de_usuario')
    return render(request, 'treinos/pedidos_compartilhamento.html', {
        'pedidos': pedidos
    })


@login_required
def aceitar_compartilhamento(request, comp_id):
    """
    Aceita um pedido de compartilhamento, marcando aceito=True
    """
    comp = get_object_or_404(CompartilhamentoTreino, id=comp_id, para_usuario=request.user)
    if not comp.aceito:
        comp.aceito = True
        comp.save()
        messages.success(request, f"Você aceitou o treino “{comp.treino.nome}” de {comp.de_usuario.username}.")
    return redirect('treinos:pedidos_compartilhamento')


@login_required
def recusar_compartilhamento(request, comp_id):
    """
    Recusa um pedido de compartilhamento, removendo o registro.
    """
    comp = get_object_or_404(CompartilhamentoTreino, id=comp_id, para_usuario=request.user)
    comp.delete()
    messages.info(request, f"Você recusou o treino “{comp.treino.nome}” de {comp.de_usuario.username}.")
    return redirect('treinos:pedidos_compartilhamento')
    
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


from itertools import chain, groupby
from collections import defaultdict
from datetime import timedelta
from io import BytesIO
import base64

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import get_user_model

import matplotlib.pyplot as plt
from matplotlib.dates import AutoDateLocator, DateFormatter

from treinos.models import Treino, ExecucaoTreino, ExecucaoExercicio, CompartilhamentoTreino
from amizades.models import PersonalInvite

@login_required
def analytics(request):
    # ——— Apenas sobrescreva target_user se:
    #      a) o usuário atual é PERSONAL e
    #      b) o GET['usuario_id'] corresponder a um aluno real dele.
    target_user = request.user
    if request.user.profile.is_personal:
        usuario_id = request.GET.get('usuario_id')
        if usuario_id:
            try:
                aluno = get_user_model().objects.get(pk=int(usuario_id))
            except get_user_model().DoesNotExist:
                aluno = None
            if aluno and (aluno in request.user.profile.students.all()):
                target_user = aluno
    # — fim da lógica de Personal

    user = target_user

    # 1) Todos os treinos (próprios + compartilhados)
    own    = Treino.objects.filter(usuario=user)
    shared = Treino.objects.filter(compartilhamentos__para_usuario=user)
    todos_treinos = list(chain(own, shared))

    # 1.1) Filtro por nome
    q = request.GET.get('q', '').strip()
    if q:
        todos_treinos = [t for t in todos_treinos if q.lower() in t.nome.lower()]

    # 2) Treino selecionado
    treino_id = request.GET.get('treino_id')
    treino = None
    if treino_id:
        try:
            t = Treino.objects.get(id=int(treino_id))
            if t.usuario == user or \
               CompartilhamentoTreino.objects.filter(treino=t, para_usuario=user).exists():
                treino = t
        except Treino.DoesNotExist:
            treino = None

    if not treino:
        return render(request, 'treinos/analytics.html', {
            'todos_treinos': todos_treinos,
            'q': q,
            'treino': None,
        })

    # 3) Período
    period = request.GET.get('period', 'all')
    hoje = timezone.localtime().date()
    if period == '1w':
        data_inicio = hoje - timedelta(weeks=1)
    elif period == '2w':
        data_inicio = hoje - timedelta(weeks=2)
    elif period == '4w':
        data_inicio = hoje - timedelta(weeks=4)
    elif period == '3m':
        data_inicio = hoje - timedelta(days=90)
    elif period == '6m':
        data_inicio = hoje - timedelta(days=180)
    else:
        data_inicio = None

    # 4) Execuções filtradas pelo período
    qs = ExecucaoTreino.objects.filter(treino=treino, usuario=user).order_by('data_inicio')
    if data_inicio:
        qs = qs.filter(data_inicio__date__gte=data_inicio)
    execucoes = list(qs)

    if not execucoes:
        return render(request, 'treinos/analytics.html', {
            'todos_treinos': todos_treinos,
            'q': q,
            'treino': treino,
            'period': period,
            'sem_execucoes': True,
        })

    primeira_data = execucoes[0].data_inicio.date()
    ultima_data   = execucoes[-1].data_inicio.date()

    # —————
    # Helper para gerar gráficos e retornar base64
    # —————
    def make_chart(x_list, y_list, title, ylabel):
        # 1) primeiro “empacotamos” e ordenamos pelo próprio x (que são datas)
        paired = sorted(zip(x_list, y_list), key=lambda pair: pair[0])
        xs, ys = zip(*paired)

        fig, ax = plt.subplots()
        ax.plot(xs, ys, marker='o', linestyle='-')  # já estará em ordem cronológica

        loc = AutoDateLocator()
        fmt = DateFormatter('%d/%m/%Y')
        ax.xaxis.set_major_locator(loc)
        ax.xaxis.set_major_formatter(fmt)
        fig.autofmt_xdate(rotation=45, ha='right')

        # Anotações de cada ponto
        for xi, yi in zip(xs, ys):
            ax.annotate(
                xi.strftime('%d/%m/%Y'),
                (xi, yi),
                textcoords="offset points",
                xytext=(0, 8),
                ha='center',
                color='#ddd',
                fontsize=8
            )

        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(True, linestyle='--', alpha=0.6)
        fig.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode()

    # —————
    # Carga total por execução
    # —————
    datas  = [e.data_inicio.date() for e in execucoes]
    cargas = [e.carga_total for e in execucoes]
    chart_carga = make_chart(datas, cargas, "Carga Total por Execução", "Carga (kg)")

    # —————
    # Total de execuções no período: como é um único ponto, mantemos a mesma lógica
    # —————
    total_exec = len(execucoes)
    chart_exec_periodo = make_chart(
        [ultima_data],
        [total_exec],
        "Execuções no Período",
        "Qtd"
    )

    # —————
    # Desempenho médio
    # —————
    hist_items = ExecucaoExercicio.objects.filter(execucao_treino__in=execucoes)
    max_por_ex = defaultdict(int)
    for item in hist_items:
        max_por_ex[item.exercicio_id] = max(max_por_ex[item.exercicio_id], item.carga_utilizada)

    datas_perf, vals_perf = [], []
    for e in execucoes:
        itens = ExecucaoExercicio.objects.filter(execucao_treino=e)
        ratios = [
            i.carga_utilizada / max_por_ex[i.exercicio_id]
            for i in itens if max_por_ex[i.exercicio_id] > 0
        ]
        pct = sum(ratios) / len(ratios) if ratios else 0
        score = 4 if pct >= 0.9 else 3 if pct >= 0.7 else 2 if pct >= 0.5 else 1
        datas_perf.append(e.data_inicio.date())
        vals_perf.append(score)
    chart_perf = make_chart(datas_perf, vals_perf, "Desempenho Médio (1=Ruim…4=Ótimo)", "")

    # —————
    # Grupos musculares (progressão por exercício)
    # —————
    groups_data = []
    all_items = ExecucaoExercicio.objects.filter(execucao_treino__in=execucoes) \
                                        .select_related('exercicio__grupo')
    sorted_items = sorted(all_items, key=lambda i: i.exercicio.grupo.nome)
    for grp_name, grp_iter in groupby(sorted_items, key=lambda i: i.exercicio.grupo.nome):
        grp_list = list(grp_iter)
        exs = []
        for ex_id, ex_name in {(i.exercicio.id, i.exercicio.nome) for i in grp_list}:
            its = [i for i in grp_list if i.exercicio.id == ex_id]
            first, last = its[0].carga_utilizada, its[-1].carga_utilizada
            pct = ((last - first) / first * 100) if first > 0 else 0
            dates  = [i.execucao_treino.data_inicio.date() for i in its]
            values = [i.carga_utilizada for i in its]
            chart = make_chart(dates, values, f"Progressão: {ex_name}", "Carga") if values else None
            exs.append({'name': ex_name, 'pct': pct, 'chart': chart})
        groups_data.append({'group': grp_name, 'exs': exs})

    period_choices = [
        ('all', 'Todos'),
        ('1w', '1 Semana'),
        ('2w', '2 Semanas'),
        ('4w', '4 Semanas'),
        ('3m', '3 Meses'),
        ('6m', '6 Meses'),
    ]

    return render(request, 'treinos/analytics.html', {
        'todos_treinos':      todos_treinos,
        'q':                  q,
        'treino':             treino,
        'period':             period,
        'primeira_data':      primeira_data,
        'ultima_data':        ultima_data,
        'chart_carga':        chart_carga,
        'chart_exec_periodo': chart_exec_periodo,
        'chart_perf':         chart_perf,
        'groups_data':        groups_data,
        'period_choices':     period_choices,
    })


from itertools import chain

@login_required
def treinos_padrao(request):
    # Busca apenas os treinos que já receberam is_padrao=True
    padroes = Treino.objects.filter(is_padrao=True)

    # Agora precisamos saber quais desses o usuário já duplicou no perfil dele:
    meus_treinos = Treino.objects.filter(usuario=request.user, is_padrao=False)
    por_nome = {t.nome: t.id for t in meus_treinos}

    mapping = {}
    for pad in padroes:
        if pad.nome in por_nome:
            mapping[pad.id] = por_nome[pad.nome]

    return render(request, 'treinos/treinos_padrao.html', {
        'treinos': padroes,
        'ja_duplicados': mapping,
    })


@login_required
def duplicar_treino_padrao(request, treino_id):
    """
    Recebe treino_id → é o ID do Treino PADRÃO (criado por staff). Após duplicar,
    cria um Treino novo (para request.user), cópia de Grupos+Exercícios,
    e redireciona para detalhe do treino criado.
    """
    padrao = get_object_or_404(Treino, id=treino_id, usuario__is_staff=True)

    # Se o usuário já tiver um treino com o mesmo nome (ou seja, já duplicou antes),
    # só redirecionamos para o detalhe desse treino:
    if Treino.objects.filter(usuario=request.user, nome=padrao.nome).exists():
        user_treino = Treino.objects.get(usuario=request.user, nome=padrao.nome)
        return redirect('treinos:detalhe_treino', pk=user_treino.id)

    # Caso contrário, criamos uma cópia completa:
    user_treino = Treino.objects.create(
        nome=padrao.nome,
        usuario=request.user,
        duracao=padrao.duracao,
        carga_total=padrao.carga_total
    )
    # Copia todos os grupos & exercícios
    for grupo in padrao.grupomuscular_set.all():
        novo_grupo = GrupoMuscular.objects.create(
            treino=user_treino,
            nome=grupo.nome
        )
        for ex in grupo.exercicio_set.all():
            Exercicio.objects.create(
                grupo=novo_grupo,
                nome=ex.nome,
                series=ex.series,
                repeticoes=ex.repeticoes,
                descanso=ex.descanso,
                carga_maxima=ex.carga_maxima
            )

    return redirect('treinos:detalhe_treino', pk=user_treino.id)



@login_required
def tornar_padrao(request, treino_id):
    treino = get_object_or_404(Treino, pk=treino_id)

    # Só staff pode marcar como padrão
    if not request.user.is_staff:
        return redirect('treinos:detalhe_treino', pk=treino.id)

    treino.is_padrao = True
    treino.save()
    return redirect('treinos:detalhe_treino', pk=treino.id)