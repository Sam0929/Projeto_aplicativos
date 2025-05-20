from django.urls import path
from . import views

app_name = 'amizades'

urlpatterns = [
    path('adicionar/', views.adicionar_ou_enviar_pedido, name='adicionar'),
    path('meus-pedidos/', views.lista_pedidos_entrada, name='pedidos_entrada'),
    path('aceitar/<int:pedido_id>/', views.aceitar_pedido, name='aceitar_pedido'),
    path('recusar/<int:pedido_id>/', views.recusar_pedido, name='recusar_pedido'),
    path('lista/', views.lista_amigos, name='lista_amigos'),
]
