from django.db import models
from django.conf import settings
from django.utils import timezone

from scheduler.models import Aluno, CustomUser
from core.models import UnidadeNegocio
from store.models import Produto


class Category(models.Model):
    TYPE_CHOICES = (
        ("income", "Entrada"),
        ("expense", "Saída"),
    )
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    unidade_negocio = models.ForeignKey(UnidadeNegocio, on_delete=models.CASCADE, related_name="categorias", null=True)

    TIPO_DRE_CHOICES = (
        ('custo', 'Custo Direto'),
        ('despesa', 'Despesa Operacional'),
    )
    tipo_dre = models.CharField(
        max_length=10,
        choices=TIPO_DRE_CHOICES,
        default='despesa',
        verbose_name="Classificação no DRE",
        help_text="Classifique como 'Custo' se for diretamente ligado à venda/serviço, ou 'Despesa' para gastos gerais."
    )

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"


class Transaction(models.Model):
    description = models.CharField(max_length=255, verbose_name="Descrição")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor")
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="transactions"
    )
    transaction_date = models.DateField(
        default=timezone.now, verbose_name="Data da Transação"
    )

    student = models.ForeignKey(
        Aluno,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_transactions",
        verbose_name="Aluno Relacionado",
    )

    professor = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_transactions",
        verbose_name="Professor Relacionado",
        limit_choices_to={'tipo__in': ['professor', 'admin']},
    )

    observation = models.TextField(blank=True, null=True, verbose_name="Observação")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    unidade_negocio = models.ForeignKey(UnidadeNegocio, on_delete=models.CASCADE, related_name="transacoes", null=True)

    def __str__(self):
        return f"{self.description} - R$ {self.amount}"

    @property
    def type(self):
        return self.category.type

    class Meta:
        ordering = ["-transaction_date"]


class Despesa(models.Model):
    STATUS_CHOICES = (
        ('a_pagar', 'A Pagar'),
        ('pago', 'Pago'),
    )
    unidade_negocio = models.ForeignKey(UnidadeNegocio, on_delete=models.CASCADE, related_name="despesas")
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey(Category, on_delete=models.PROTECT, limit_choices_to={'type': 'expense'})
    data_competencia = models.DateField(verbose_name="Mês de Competência")
    data_pagamento = models.DateField(null=True, blank=True, verbose_name="Data do Pagamento")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='a_pagar')
    professor = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="despesas",
        verbose_name="Professor Relacionado",
        limit_choices_to={'tipo__in': ['professor', 'admin']}
    )
    transacao = models.OneToOneField(Transaction, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Despesa: {self.descricao} ({self.get_status_display()})"


class Receita(models.Model):
    STATUS_CHOICES = (
        ('a_receber', 'A Receber'),
        ('recebido', 'Recebido'),
    )
    unidade_negocio = models.ForeignKey(UnidadeNegocio, on_delete=models.CASCADE, related_name="receitas")
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey(Category, on_delete=models.PROTECT, limit_choices_to={'type': 'income'})
    data_competencia = models.DateField(verbose_name="Mês de Competência")
    data_recebimento = models.DateField(null=True, blank=True, verbose_name="Data do Recebimento")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='a_receber')
    aluno = models.ForeignKey(
        Aluno,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="receitas",
        verbose_name="Aluno Relacionado"
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receitas",
        verbose_name="Produto Relacionado"
    )
    quantidade = models.PositiveIntegerField(
        default=1,
        null=True,
        blank=True,
        verbose_name="Quantidade Vendida"
    )
    transacao = models.OneToOneField(Transaction, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Receita: {self.descricao} ({self.get_status_display()})"


class DespesaRecorrente(models.Model):
    unidade_negocio = models.ForeignKey(UnidadeNegocio, on_delete=models.CASCADE, related_name="despesas_recorrentes")
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey(Category, on_delete=models.PROTECT, limit_choices_to={'type': 'expense'})
    dia_do_mes = models.PositiveIntegerField(verbose_name="Dia do Mês para Lançamento")
    data_inicio = models.DateField(default=timezone.now, verbose_name="Início da Recorrência")
    data_fim = models.DateField(null=True, blank=True, verbose_name="Fim da Recorrência")
    professor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="despesas_recorrentes", limit_choices_to={'tipo__in': ['professor', 'admin']})
    ativa = models.BooleanField(default=True, verbose_name="Está ativa?")

    def __str__(self):
        return f"Recorrente: {self.descricao} (Todo dia {self.dia_do_mes})"


class ReceitaRecorrente(models.Model):
    unidade_negocio = models.ForeignKey(UnidadeNegocio, on_delete=models.CASCADE, related_name="receitas_recorrentes")
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dia_do_mes = models.PositiveIntegerField(verbose_name="Dia do Mês para Lançamento", null=True, blank=True)
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="receitas_recorrentes", null=True, blank=True)
    categoria = models.ForeignKey(Category, on_delete=models.PROTECT, limit_choices_to={'type': 'income'})
    data_inicio = models.DateField(default=timezone.now, verbose_name="Início da Recorrência")
    data_fim = models.DateField(null=True, blank=True, verbose_name="Fim da Recorrência")
    ativa = models.BooleanField(default=True, verbose_name="Está ativa?")
    
    def __str__(self):
        return f"Recorrente: {self.descricao} - {self.aluno.nome_completo} (Todo dia {self.dia_do_mes})"
