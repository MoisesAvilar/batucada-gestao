from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from urllib.parse import quote as urlquote
import json

from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Interface de Admin rica para o modelo AuditLog.
    """

    # --- Configurações da Lista de Logs ---

    list_display = ('timestamp', 'username', 'colored_action', 'resource_link', 'ip_address', 'method', 'path')
    list_filter = ('action', 'resource_type', ('user', admin.RelatedOnlyFieldListFilter), 'timestamp')
    search_fields = ('username', 'ip_address', 'resource_name', 'resource_id', 'path', 'detail')
    list_per_page = 50

    # --- Configurações da Tela de Detalhes (Read-Only) ---

    # Define os campos como somente leitura
    readonly_fields = [field.name for field in AuditLog._meta.fields] + ['formatted_detail', 'formatted_metadata']

    # Organiza os campos em seções na tela de detalhes
    fieldsets = (
        ('QUEM & QUANDO', {
            'fields': ('timestamp', 'user', 'username', 'ip_address')
        }),
        ('O QUE ACONTECEU', {
            'fields': ('colored_action', 'resource_type', 'resource_name', 'resource_id')
        }),
        ('DETALHES DA AÇÃO', {
            'fields': ('formatted_detail', 'formatted_metadata'),
            'classes': ('collapse',), # Começa recolhido
        }),
        ('METADADOS DA REQUISIÇÃO', {
            'fields': ('path', 'method', 'user_agent', 'tags'),
            'classes': ('collapse',),
        }),
    )

    # --- Métodos Customizados para Melhorar a Exibição ---

    @admin.display(description='Ação', ordering='action')
    def colored_action(self, obj):
        """Exibe a ação com um badge colorido."""
        colors = {
            'criou': 'success',
            'atualizou': 'warning',
            'deletou': 'danger',
            'visualizou': 'secondary',
        }
        color = colors.get(obj.action.lower(), 'primary')
        return format_html(
            '<span style="color: white; background-color: var(--bs-{}); padding: 3px 8px; border-radius: 5px;">{}</span>',
            color,
            obj.action.title()
        )

    @admin.display(description='Recurso', ordering='resource_name')
    def resource_link(self, obj):
        """Cria um link para o recurso no admin, se possível."""
        if obj.resource_type and obj.resource_type != 'http' and obj.resource_id:
            # Tenta montar a URL do admin para o objeto (ex: /admin/auth/user/1/)
            try:
                admin_url = reverse(
                    f'admin:{obj._meta.app_label}_{obj.resource_type.lower()}_change',
                    args=[urlquote(obj.resource_id)]
                )
                return format_html('<a href="{}">{} #{}</a>', admin_url, obj.resource_name, obj.resource_id)
            except Exception:
                # Se não conseguir resolver a URL, mostra apenas o texto
                pass
        return obj.resource_name or f"{obj.resource_type} #{obj.resource_id}"

    @admin.display(description='Detalhes Formatados')
    def formatted_detail(self, obj):
        """Formata o campo JSON 'detail' para melhor legibilidade."""
        if obj.detail:
            pretty_json = json.dumps(obj.detail, indent=4, ensure_ascii=False)
            return format_html('<pre style="white-space: pre-wrap; word-break: break-all;">{}</pre>', pretty_json)
        return "N/A"

    @admin.display(description='Metadata Formatado')
    def formatted_metadata(self, obj):
        """Formata o campo JSON 'metadata' para melhor legibilidade."""
        if obj.metadata:
            pretty_json = json.dumps(obj.metadata, indent=4, ensure_ascii=False)
            return format_html('<pre style="white-space: pre-wrap; word-break: break-all;">{}</pre>', pretty_json)
        return "N/A"

    # --- Permissões (Interface Somente Leitura) ---

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False # Permite ver, mas não alterar

    def has_delete_permission(self, request, obj=None):
        return False