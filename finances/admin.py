from django.contrib import admin
from .models import Category, Transaction, Despesa, Receita, DespesaRecorrente, ReceitaRecorrente


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "type")
    list_filter = ("type",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'category', 'transaction_date', 'student', 'professor')
    list_filter = ('category__type', 'category', 'transaction_date')
    search_fields = ('description', 'student__nome_completo', 'professor__username', 'observation')
    autocomplete_fields = ('category', 'student', 'professor', 'created_by')
    ordering = ('-transaction_date',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Despesa)
class DespesaAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'valor', 'categoria', 'data_competencia', 'status', 'unidade_negocio')
    list_filter = ('status', 'unidade_negocio', 'data_competencia')
    search_fields = ('descricao',)
    ordering = ('-data_competencia',)


@admin.register(Receita)
class ReceitaAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'valor', 'categoria', 'data_competencia', 'status', 'unidade_negocio')
    list_filter = ('status', 'unidade_negocio', 'data_competencia')
    search_fields = ('descricao', 'aluno__nome_completo')
    ordering = ('-data_competencia',)


@admin.register(DespesaRecorrente)
class DespesaRecorrenteAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'valor', 'dia_do_mes', 'ativa', 'unidade_negocio')

@admin.register(ReceitaRecorrente)
class ReceitaRecorrenteAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'aluno', 'valor', 'dia_do_mes', 'ativa', 'unidade_negocio')