from django.db import models
from core.models import UnidadeNegocio
from decimal import Decimal


class CategoriaProduto(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    unidade_negocio = models.ForeignKey(
        UnidadeNegocio, on_delete=models.CASCADE, related_name="categorias_de_produto"
    )

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Categoria de Produto"
        verbose_name_plural = "Categorias de Produtos"


class Produto(models.Model):
    unidade_negocio = models.ForeignKey(
        UnidadeNegocio, on_delete=models.CASCADE, related_name="produtos"
    )

    # --- Informações Básicas ---
    nome = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, null=True)
    categoria = models.ForeignKey(
        CategoriaProduto, on_delete=models.SET_NULL, null=True, blank=True
    )

    # --- Controle de Estoque ---
    sku = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name="SKU / Cód. de Barras",
    )
    quantidade_em_estoque = models.PositiveIntegerField(
        default=0, verbose_name="Qtd. em Estoque"
    )

    # --- Custos e Precificação ---
    custo_de_aquisicao = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Custo de Aquisição"
    )
    percentual_markup = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=40.00,
        verbose_name="Markup (%)",
        help_text="Percentual de lucro desejado sobre o custo.",
    )
    preco_de_venda_manual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Preço de Venda Manual (Opcional)",
    )

    def __str__(self):
        return self.nome

    @property
    def preco_de_venda_calculado(self):
        if self.preco_de_venda_manual:
            return self.preco_de_venda_manual
        if self.custo_de_aquisicao and self.percentual_markup:
            markup_decimal = self.percentual_markup / Decimal(100)
            return self.custo_de_aquisicao * (1 + markup_decimal)
        return Decimal("0.00")

    @property
    def lucro_bruto_por_unidade(self):
        return self.preco_de_venda_calculado - self.custo_de_aquisicao

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
