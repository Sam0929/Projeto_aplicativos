from django.contrib import admin

from django.contrib import admin
from .models import PedidoAmizade, Amizade

@admin.register(PedidoAmizade)
class PedidoAmizadeAdmin(admin.ModelAdmin):
    list_display = ('de_usuario', 'para_usuario', 'data_criacao', 'aceito')
    list_filter = ('aceito',)
    search_fields = ('de_usuario__username', 'para_usuario__username')

@admin.register(Amizade)
class AmizadeAdmin(admin.ModelAdmin):
    list_display = ('usuario1', 'usuario2', 'data_amizade')
    search_fields = ('usuario1__username', 'usuario2__username')
