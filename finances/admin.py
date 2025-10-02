from django.contrib import admin
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.html import format_html
from django.db.models import Sum

from .models import Category, Transaction, Despesa, Receita, DespesaRecorrente, ReceitaRecorrente
from .filters import AnoFilter


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "type",
        "transaction_count_link",
        "despesa_count_link",
        "receita_count_link",
        "despesa_recorrente_count_link",
        "receita_recorrente_count_link",
    )
    list_filter = ("type", "tipo_dre")
    search_fields = ("name",)
    ordering = ("name",)

    # --- LINKS CLICÁVEIS ---

    def transaction_count_link(self, obj):
        count = obj.transactions.count()
        url = (
            reverse("admin:finances_transaction_changelist")
            + "?"
            + urlencode({"category__id": str(obj.id)})
        )
        return format_html('<a href="{}">{}</a>', url, count)
    transaction_count_link.short_description = "Transações"

    def despesa_count_link(self, obj):
        count = obj.despesa_set.count()
        url = (
            reverse("admin:finances_despesa_changelist")
            + "?"
            + urlencode({"categoria__id": str(obj.id)})
        )
        return format_html('<a href="{}">{}</a>', url, count)
    despesa_count_link.short_description = "Despesas"

    def receita_count_link(self, obj):
        count = obj.receita_set.count()
        url = (
            reverse("admin:finances_receita_changelist")
            + "?"
            + urlencode({"categoria__id": str(obj.id)})
        )
        return format_html('<a href="{}">{}</a>', url, count)
    receita_count_link.short_description = "Receitas"

    def despesa_recorrente_count_link(self, obj):
        count = obj.despesarecorrente_set.count()
        url = (
            reverse("admin:finances_despesarecorrente_changelist")
            + "?"
            + urlencode({"categoria__id": str(obj.id)})
        )
        return format_html('<a href="{}">{}</a>', url, count)
    despesa_recorrente_count_link.short_description = "Despesas Recorrentes"

    def receita_recorrente_count_link(self, obj):
        count = obj.receitarecorrente_set.count()
        url = (
            reverse("admin:finances_receitarecorrente_changelist")
            + "?"
            + urlencode({"categoria__id": str(obj.id)})
        )
        return format_html('<a href="{}">{}</a>', url, count)
    receita_recorrente_count_link.short_description = "Receitas Recorrentes"


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
    list_filter = ('status', 'unidade_negocio', 'data_competencia', AnoFilter)
    search_fields = ('descricao',)
    ordering = ('-data_competencia',)

    actions = ['calcular_total']

    def calcular_total(self, request, queryset):
        total = queryset.aggregate(Sum('valor'))['valor__sum'] or 0
        self.message_user(request, f"💰 Total das despesas selecionadas: R$ {total:.2f}")
    calcular_total.short_description = "Calcular total das despesas selecionadas"


@admin.register(Receita)
class ReceitaAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'valor', 'categoria', 'data_competencia', 'status', 'unidade_negocio')
    list_filter = ('status', 'unidade_negocio', 'data_competencia', AnoFilter)
    search_fields = ('descricao', 'aluno__nome_completo')
    ordering = ('-data_competencia',)

    actions = ['calcular_total']

    def calcular_total(self, request, queryset):
        total = queryset.aggregate(Sum('valor'))['valor__sum'] or 0
        self.message_user(request, f"💰 Total das receitas selecionadas: R$ {total:.2f}")
    calcular_total.short_description = "Calcular total das receitas selecionadas"


@admin.register(DespesaRecorrente)
class DespesaRecorrenteAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'valor', 'dia_do_mes', 'ativa', 'unidade_negocio')

@admin.register(ReceitaRecorrente)
class ReceitaRecorrenteAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'aluno', 'valor', 'dia_do_mes', 'ativa', 'unidade_negocio')