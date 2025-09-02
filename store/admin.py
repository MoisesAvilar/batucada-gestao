from django.contrib import admin
from .models import CategoriaProduto, Produto


@admin.register(CategoriaProduto)
class CategoriaProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "unidade_negocio")
    list_filter = ("unidade_negocio",)
    search_fields = ("nome",)
    ordering = ("nome",)


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "categoria",
        "custo_de_aquisicao",
        "preco_de_venda_calculado",
        "quantidade_em_estoque",
        "unidade_negocio",
    )
    list_filter = ("unidade_negocio", "categoria")
    search_fields = ("nome", "sku", "descricao")
    ordering = ("nome",)

    # Exibe os campos @property como readonly
    readonly_fields = ("preco_de_venda_calculado", "lucro_bruto_por_unidade")

    fieldsets = (
        (
            "Informações Gerais",
            {"fields": ("unidade_negocio", "nome", "sku", "categoria", "descricao")},
        ),
        (
            "Estoque e Custos",
            {"fields": ("quantidade_em_estoque", "custo_de_aquisicao")},
        ),
        (
            "Precificação",
            {
                "fields": (
                    "percentual_markup",
                    "preco_de_venda_manual",
                    "preco_de_venda_calculado",
                    "lucro_bruto_por_unidade",
                )
            },
        ),
    )
