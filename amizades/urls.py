from django.urls import path
from . import views

app_name = 'amizades'

urlpatterns = [
    path('adicionar/', views.adicionar_ou_enviar_pedido, name='adicionar'),
    path('meus-pedidos/', views.lista_pedidos_entrada, name='pedidos_entrada'),
    path('aceitar/<int:pedido_id>/', views.aceitar_pedido, name='aceitar_pedido'),
    path('recusar/<int:pedido_id>/', views.recusar_pedido, name='recusar_pedido'),
    path('lista/', views.lista_amigos, name='lista_amigos'),
    path('meus-alunos/', views.meus_alunos, name='meus_alunos'),
    path('enviar-convite/<int:amigo_id>/', views.enviar_convite_aluno, name='enviar_convite_aluno'),
    path('aceitar-convite/<int:pk>/', views.aceitar_convite, name='aceitar_convite'),
    path('remover-aluno/<int:user_id>/', views.remover_aluno, name='remover_aluno'),
    path('meus-personals/', views.meus_personals, name='meus_personals'),
]
