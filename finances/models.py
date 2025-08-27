from django.db import models
from django.conf import settings
from django.utils import timezone

from scheduler.models import Aluno, CustomUser


class Category(models.Model):
    TYPE_CHOICES = (
        ("income", "Entrada"),
        ("expense", "Saída"),
    )
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)

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

    # Campos de auditoria
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.description} - R$ {self.amount}"

    @property
    def type(self):
        return self.category.type

    class Meta:
        ordering = ["-transaction_date"]
