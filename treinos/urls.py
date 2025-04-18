from django.urls import path
from . import views

app_name = 'treinos'

urlpatterns = [
    path('', views.lista_treinos, name='lista_treinos'),
    path('novo/', views.novo_treino, name='novo_treino'),
    path('<int:pk>/', views.detalhe_treino, name='detalhe_treino'),
    path('historico/', views.historico_treino, name='historico_treino'),
]