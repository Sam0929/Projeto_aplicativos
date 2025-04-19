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
    path('<int:pk>/iniciar/', views.iniciar_treino, name='iniciar_treino'),
]