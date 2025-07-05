from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class CustomUser(AbstractUser):
    TIPO_USUARIO_CHOICES = (
        ("admin", "Administrador"),
        ("professor", "Professor"),
    )
    tipo = models.CharField(
        max_length=15,
        choices=TIPO_USUARIO_CHOICES,
        default="professor",
        verbose_name="Tipo de Usuário",
    )
    profile_picture_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="URL da Foto de Perfil"
    )


class Aluno(models.Model):
    nome_completo = models.CharField(max_length=255, verbose_name="Nome Completo")
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_completo


class Modalidade(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome


class Aula(models.Model):
    STATUS_AULA_CHOICES = (
        ("Agendada", "Agendada"),
        ("Realizada", "Realizada"),
        ("Cancelada", "Cancelada"),
        ("Aluno Ausente", "Aluno Ausente"),
    )
    aluno = models.ForeignKey("Aluno", on_delete=models.CASCADE, verbose_name="Aluno")
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"tipo": "professor"},
        verbose_name="Professor Atribuído",
    )
    modalidade = models.ForeignKey(
        Modalidade, on_delete=models.PROTECT, verbose_name="Modalidade"
    )
    data_hora = models.DateTimeField(verbose_name="Data e Horário")
    status = models.CharField(
        max_length=20, choices=STATUS_AULA_CHOICES, default="Agendada"
    )
    def __str__(self):
        return f"{self.modalidade} com {self.aluno.nome_completo} em {self.data_hora.strftime('%d/%m/%Y %H:%M')}"


class RelatorioAula(models.Model):
    aula = models.OneToOneField(Aula, on_delete=models.CASCADE, primary_key=True)
    conteudo_teorico = models.TextField(
        verbose_name="Conteúdo Teórico Abordado", blank=True, null=True
    )
    exercicios_rudimentos = models.TextField(
        verbose_name="Exercícios de Rudimentos", blank=True, null=True
    )
    bpm_rudimentos = models.CharField(
        max_length=100, verbose_name="BPM dos Rudimentos", blank=True, null=True
    )
    exercicios_ritmo = models.TextField(
        verbose_name="Exercícios de Ritmo", blank=True, null=True
    )
    livro_ritmo = models.CharField(
        max_length=200, verbose_name="Livro/Método de Ritmo", blank=True, null=True
    )
    clique_ritmo = models.CharField(
        max_length=100, verbose_name="Clique/BPM do Ritmo", blank=True, null=True
    )
    exercicios_viradas = models.TextField(
        verbose_name="Exercícios de Viradas", blank=True, null=True
    )
    clique_viradas = models.CharField(
        max_length=100, verbose_name="Clique/BPM das Viradas", blank=True, null=True
    )
    repertorio_musicas = models.TextField(
        verbose_name="Músicas do Repertório", blank=True, null=True
    )
    observacoes_gerais = models.TextField(
        verbose_name="Observações Gerais sobre a Aula", blank=True, null=True
    )
    professor_que_validou = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"tipo": "professor"},
        related_name="aulas_validadas_por_mim",
        verbose_name="Professor que Realizou a Aula",
    )

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Relatório da aula de {self.aula.aluno.nome_completo} em {self.aula.data_hora.strftime('%d/%m/%Y')}"
