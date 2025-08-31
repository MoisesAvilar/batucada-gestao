from django.db import models


class UnidadeNegocio(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Unidade")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Unidade de Negócio"
        verbose_name_plural = "Unidades de Negócio"
