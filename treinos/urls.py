from django.urls import path
from . import views

app_name = 'treinos'

urlpatterns = [
    path('', views.lista_treinos, name='lista_treinos'),
    path('novo/', views.novo_treino, name='novo_treino'),
    path('<int:pk>/', views.detalhe_treino, name='detalhe_treino'),
    path('<int:pk>/editar/', views.editar_treino, name='editar_treino'),
    path('<int:pk>/excluir/', views.excluir_treino, name='excluir_treino'),
    path('historico/', views.historico_treino, name='historico_treino'),
    path('<int:pk>/editar/', views.editar_treino, name='editar_treino'),
    path('<int:pk>/excluir/', views.excluir_treino, name='excluir_treino'),
    path('<int:treino_id>/iniciar/', views.iniciar_treino, name='iniciar_treino'),
    path('compartilhar/<int:treino_id>/', views.compartilhar_treino, name='compartilhar_treino'),
    path('<int:pk>/adicionar/', views.adicionar_treino, name='adicionar_treino'),
    path('pedidos_compartilhamento/', views.lista_pedidos_compartilhamento, name='pedidos_compartilhamento'),
    path('aceitar_compartilhamento/<int:comp_id>/', views.aceitar_compartilhamento, name='aceitar_compartilhamento'),
    path('recusar_compartilhamento/<int:comp_id>/', views.recusar_compartilhamento, name='recusar_compartilhamento'),
    path('analytics/', views.analytics, name='analytics'),
    path('padrao/', views.treinos_padrao, name='treinos_padrao'),
    path('padrao/<int:treino_id>/duplicar/', views.duplicar_treino_padrao, name='duplicar_treino_padrao'),
    path('<int:treino_id>/tornar-padrao/', views.tornar_padrao, name='tornar_padrao'),
]