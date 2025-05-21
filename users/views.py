from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
from django.contrib.auth.decorators import login_required
from treinos.models import Treino, ExecucaoTreino,CompartilhamentoTreino,ExecucaoExercicio
from .forms import RegisterForm, LoginForm, UpdateUserForm, UpdateProfileForm 
from django.contrib.auth import get_user_model
from amizades.models import Amizade, PedidoAmizade
from django.db.models import Q
from django.db.models import Count, Max
import collections
from collections import defaultdict, Counter


@login_required
def home(request):
    # Estatísticas rápidas
    treinos_count = Treino.objects.filter(usuario=request.user).count()
    exec_count    = ExecucaoTreino.objects.filter(usuario=request.user).count()
    last_exec     = ExecucaoTreino.objects.filter(usuario=request.user) \
                        .order_by('-data_inicio') \
                        .first()

    # Contagem de treinos compartilhados com o usuário
    shared_count = Treino.objects.filter(
        compartilhamentos__para_usuario=request.user
    ).distinct().count()

    return render(request, 'users/home.html', {
        'treinos_count':   treinos_count,
        'exec_count':      exec_count,
        'last_exec':       last_exec,
        'shared_count':    shared_count,
    })


class RegisterView(View):
    
    form_class = RegisterForm
    initial = {'key': 'value'}
    template_name = 'users/register.html'

    def dispatch(self, request, *args, **kwargs):
        # will redirect to the home page if a user tries to access the register page while logged in
        if request.user.is_authenticated:
            return redirect(to='/')

        # else process dispatch as it otherwise normally would
        return super(RegisterView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            form.save()

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}')

            return redirect(to='login')

        return render(request, self.template_name, {'form': form})


# Class based view that extends from the built in login view to add a remember me functionality
class CustomLoginView(LoginView):
    form_class = LoginForm

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')

        if not remember_me:
            # set session expiry to 0 seconds. So it will automatically close the session after the browser is closed.
            self.request.session.set_expiry(0)

            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
        return super(CustomLoginView, self).form_valid(form)


class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject'
    success_message = "We've emailed you instructions for setting your password, " \
                      "if an account exists with the email you entered. You should receive them shortly." \
                      " If you don't receive an email, " \
                      "please make sure you've entered the address you registered with, and check your spam folder."
    success_url = reverse_lazy('users:users-home')


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'users/change_password.html'
    success_message = "Successfully Changed Your Password"
    success_url = reverse_lazy('users:users-home')


@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UpdateUserForm(request.POST, instance=request.user)
        profile_form = UpdateProfileForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile is updated successfully')
            return redirect(to='users:users-profile')
    else:
        user_form = UpdateUserForm(instance=request.user)
        profile_form = UpdateProfileForm(instance=request.user.profile)

    return render(request, 'users/profile.html', {'user_form': user_form, 'profile_form': profile_form})


User = get_user_model()

@login_required
def profile_detail(request, username):
    usuario = get_object_or_404(User, username=username)

    # interesses
    interests_list = []
    if usuario.profile.interests:
        interests_list = [
            tag.strip()
            for tag in usuario.profile.interests.split(',')
            if tag.strip()
        ]

    # dados de academia (já no objeto profile)
    profile = usuario.profile

    return render(request, 'users/profile_detail.html', {
        'usuario': usuario,
        'interests_list': interests_list,
        'profile': profile,
        'is_me': usuario == request.user,
    })
    
@login_required
def profile_treinos(request, username):
    """
    Exibe todos os treinos do usuário 'username', 
    sem necessidade de compartilhamento.
    Se for o próprio request.user, redireciona para lista_treinos padrão.
    """
    user_alvo = get_object_or_404(User, username=username)

    if user_alvo == request.user:
        return redirect('treinos:lista_treinos')

    # Agora traz todos os treinos desse user_alvo
    treinos = Treino.objects.filter(
        usuario=user_alvo
    ).prefetch_related('grupomuscular_set')

    return render(request, 'users/profile_treinos.html', {
        'treinos': treinos,
        'user_alvo': user_alvo
    })
    

@login_required
def profile_historico(request, username):
    usuario = get_object_or_404(User, username=username)

    # 1) Busque todas as execuções desse usuário, em ordem decrescente de data
    execucoes = (
        ExecucaoTreino.objects
        .filter(usuario=usuario)
        .select_related('treino')
        .order_by('-data_inicio')
    )

    # 2) Preparar estatísticas globais (modo e máxima) para cada treino_id e exercicio_id
    #    Estrutura: global_stats[treino_id][exercicio_id] = {'moda': …, 'maxima': …}
    global_stats = {}
    treino_ids = {e.treino_id for e in execucoes}
    for tid in treino_ids:
        itens_hist = ExecucaoExercicio.objects.filter(
            execucao_treino__treino_id=tid
        )
        # Agrupa todas as cargas já usadas (histórico) por exercício
        cargas_por_ex = defaultdict(list)
        for ih in itens_hist:
            cargas_por_ex[ih.exercicio_id].append(ih.carga_utilizada)

        stats = {}
        for eid, cargas in cargas_por_ex.items():
            # calcula carga que mais repetiu (modo) e carga máxima daquele exercício
            stats[eid] = {
                'moda': Counter(cargas).most_common(1)[0][0],
                'maxima': max(cargas),
            }
        global_stats[tid] = stats

    # 3) Para cada execução, monte a estrutura em Python para passar ao template
    execucoes_data = []
    for execucao in execucoes:
        # carrega as estatísticas daquele treino específico
        stats_do_treino = global_stats.get(execucao.treino_id, {})

        # busque todas as ExecucaoExercicio desta execução, junto com exercicio
        itens_exec = (
            ExecucaoExercicio.objects
            .filter(execucao_treino=execucao)
            .select_related('exercicio')
            .order_by('serie')
        )

        # Agrupa as séries por exercício
        usadas_por_ex = defaultdict(list)
        # Também vamos coletar, para cada série, o índice de desempenho
        perf_indices = []

        for item in itens_exec:
            # armazenamos o objeto inteiro para depois iterar por grupo
            usadas_por_ex[item.exercicio].append(item)

        detalhes_grupos = []
        # Para cada grupo muscular daquele treino, precisamos agrupar exercícios
        # Para isso, repetiremos a lógica do historial, mas mantendo a ordem dos grupos:
        for grupo in execucao.treino.grupomuscular_set.all().prefetch_related('exercicio_set'):
            grupo_dict = {
                'nome_grupo': grupo.nome,
                'exercicios': []
            }

            for ex in grupo.exercicio_set.all():
                # Para esse exercício, pegue as ExecucaoExercicio(es) da execução atual:
                series_exec = usadas_por_ex.get(ex, [])

                # Lista de dicionários com {'serie': …, 'carga': …, 'duracao': …}
                series_details = []
                for ce in series_exec:
                    series_details.append({
                        'serie': ce.serie,
                        'carga': ce.carga_utilizada,
                        'duracao': ce.duracao,  # timedelta
                    })

                # Dados históricos (modo e máxima) para ex.id
                hist = stats_do_treino.get(ex.id, {'moda': 0, 'maxima': 0})
                carga_moda = hist['moda']
                carga_max  = hist['maxima']

                # Calcule índices de desempenho para cada série desse exercício
                for ce in series_exec:
                    if carga_max > 0:
                        perf_indices.append(ce.carga_utilizada / carga_max)

                grupo_dict['exercicios'].append({
                    'nome_ex': ex.nome,
                    'series_details': series_details,
                    'carga_moda': carga_moda,
                    'carga_max': carga_max,
                })

            detalhes_grupos.append(grupo_dict)

        # 4) Calcule desempenho geral da execução (média de índices de série)
        pct = sum(perf_indices) / len(perf_indices) if perf_indices else 0
        if pct >= 0.9:
            desempenho = 'Ótimo'
        elif pct >= 0.7:
            desempenho = 'Bom'
        elif pct >= 0.5:
            desempenho = 'Regular'
        else:
            desempenho = 'Ruim'

        # 5) Duração total em minutos
        min_total = int(execucao.duracao.total_seconds() // 60)

        execucoes_data.append({
            'id': execucao.id,
            'nome_treino': execucao.treino.nome,
            'data_inicio': execucao.data_inicio,
            'duracao_minutos': min_total,
            'desempenho': desempenho,
            'detalhes': detalhes_grupos,
        })

    return render(request, 'users/profile_historico.html', {
        'usuario': usuario,
        'execucoes_data': execucoes_data,
    })