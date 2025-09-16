from django.contrib import admin
from .models import UnidadeNegocio, Notificacao  # <<< 1. Importar o modelo Notificacao


@admin.register(UnidadeNegocio)
class UnidadeNegocioAdmin(admin.ModelAdmin):
    """
    Configuração da interface de admin para o modelo UnidadeNegocio.
    """

    list_display = ("nome",)
    search_fields = ("nome",)
    ordering = ("nome",)


# --- INÍCIO DA ADIÇÃO ---
# vvv 2. Registrar o novo modelo Notificacao vvv
@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    """
    Configuração da interface de admin para o modelo Notificacao.
    Útil para debugar e ver todas as notificações geradas.
    """

    list_display = ("usuario", "titulo", "lida", "tipo", "data_criacao")
    list_filter = ("lida", "tipo", "data_criacao")
    search_fields = ("usuario__username", "titulo", "mensagem")
    ordering = ("-data_criacao",)
    # Deixa o campo de texto de mensagem mais fácil de ler
    readonly_fields = ("data_criacao",)


# --- FIM DA ADIÇÃO ---
