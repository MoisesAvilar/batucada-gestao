from django.contrib import admin
from .models import UnidadeNegocio


@admin.register(UnidadeNegocio)
class UnidadeNegocioAdmin(admin.ModelAdmin):
    """
    Configuração da interface de admin para o modelo UnidadeNegocio.
    """

    list_display = ("nome",)
    search_fields = ("nome",)
    ordering = ("nome",)
