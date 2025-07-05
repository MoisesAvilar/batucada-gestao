from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Aluno, Modalidade, Aula


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Customização para o modelo de Usuário.
    Herda de UserAdmin para manter toda a funcionalidade padrão de usuários do Django.
    """

    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("tipo",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {"fields": ("tipo",)}),)
    list_display = ["username", "email", "first_name", "last_name", "tipo", "is_staff"]
    list_filter = UserAdmin.list_filter + ("tipo",)


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    """
    Customização para o modelo de Aluno.
    """

    list_display = ["nome_completo", "email", "telefone", "data_criacao"]
    search_fields = ["nome_completo", "email"]


@admin.register(Modalidade)
class ModalidadeAdmin(admin.ModelAdmin):
    """
    Customização para o modelo de Modalidade.
    """

    search_fields = ["nome"]


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    """
    Customização para o modelo de Aula, o mais importante.
    """

    list_display = ["aluno", "professor", "modalidade", "data_hora", "status"]
    list_filter = ["status", "professor", "modalidade", "data_hora"]
    search_fields = ["aluno__nome_completo", "professor__username"]
    autocomplete_fields = ["aluno", "professor"]
    list_editable = ["status"]
    ordering = ["-data_hora"]
