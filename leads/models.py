from django.db import models
from django.conf import settings
from core.models import UnidadeNegocio
from scheduler.models import Aluno
from datetime import date


def get_escola_unidade_negocio():
    try:
        return UnidadeNegocio.objects.get(nome="Escola")
    except UnidadeNegocio.DoesNotExist:
        return None


def smart_title(text):
    if not text:
        return text

    preps = {"de", "da", "das", "do", "dos", "e"}

    words = text.lower().split()
    result = []

    for i, word in enumerate(words):
        if i == 0:
            result.append(word.capitalize())
            continue

        if word in preps:
            result.append(word)
        else:
            result.append(word.capitalize())

    return " ".join(result)


class Lead(models.Model):
    STATUS_CHOICES = (
        ("novo", "Novo"),
        ("em_contato", "Em Contato"),
        ("negociando", "Negociando"),
        ("perdido", "Perdido"),
    )

    nome_interessado = models.CharField(
        max_length=255, verbose_name="Nome do Interessado"
    )
    nome_responsavel = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Nome do Responsável (se aplicável)",
    )
    contato = models.CharField(max_length=100, help_text="Telefone ou E-mail")
    idade = models.PositiveIntegerField(null=True, blank=True)
    fonte = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Fonte do Lead",
        help_text="Ex: Instagram, Indicação, etc.",
    )

    CURSO_CHOICES = sorted([
        ("batera_facil", "Batera no Fácil"),
        ("personalizado_batucada", "Personalizado Batucada"),
        ("mentoria_black_batucada", "Mentoria Black Batucada"),
        ("baixo", "Baixo"),
        ("guitarra", "Guitarra"),
        ("teclado", "Teclado"),
        ("canto", "Canto"),
        ("outro", "Outro"),
    ], key=lambda x: x[1])

    NIVEL_CHOICES = (
        ("iniciante", "Iniciante (nunca toquei)"),
        ("basico", "Básico (já tive algum contato)"),
        ("intermediario", "Intermediário (toco por hobby)"),
        ("avancado", "Avançado (busco aperfeiçoamento)"),
    )

    HORARIO_CHOICES = (
        ("manha", "Manhã (08:00 - 12:00)"),
        ("tarde", "Tarde (14:00 - 17:00)"),
        ("noite", "Noite (18:00 - 21:00)"),
    )

    curso_interesse = models.CharField(
        max_length=50,
        choices=CURSO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Curso de Interesse",
    )
    nivel_experiencia = models.CharField(
        max_length=50,
        choices=NIVEL_CHOICES,
        blank=True,
        null=True,
        verbose_name="Nível de Experiência",
    )
    melhor_horario_contato = models.CharField(
        max_length=50,
        choices=HORARIO_CHOICES,
        blank=True,
        null=True,
        verbose_name="Horário da Aula",
    )
    observacoes = models.TextField(
        blank=True, null=True, verbose_name="Observações"
    )

    proposito_estudo = models.TextField(
        blank=True, null=True, verbose_name="Qual seu propósito de estudar bateria?"
    )
    objetivo_tocar = models.TextField(
        blank=True, null=True, verbose_name="Onde você gostaria de tocar?"
    )
    motivo_interesse_especifico = models.TextField(
        blank=True, null=True, verbose_name="Algo em específico que te fez interessar pela bateria?"
    )
    sobre_voce = models.TextField(
        blank=True, null=True, verbose_name="Conte um pouco sobre você"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="novo")
    data_criacao = models.DateField(default=date.today, verbose_name="Data de Criação")

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads_criados",
        verbose_name="Criado por",
    )

    unidade_negocio = models.ForeignKey(
        UnidadeNegocio,
        on_delete=models.PROTECT,
        default=get_escola_unidade_negocio
    )

    aluno_convertido = models.OneToOneField(
        Aluno,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_origem",
    )

    convertido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads_convertidos",
        verbose_name="Convertido por",
    )

    def __str__(self):
        return self.nome_interessado

    def save(self, *args, **kwargs):

        if self.nome_interessado:
            self.nome_interessado = smart_title(self.nome_interessado)

        if self.nome_responsavel:
            self.nome_responsavel = smart_title(self.nome_responsavel)

        if self.fonte:
            self.fonte = smart_title(self.fonte)

        super().save(*args, **kwargs)


class InteracaoLead(models.Model):
    TIPO_CHOICES = (
        ("ligacao", "Ligação Telefônica"),
        ("email", "E-mail"),
        ("whatsapp", "Mensagem (WhatsApp)"),
        ("visita", "Visita Presencial"),
        ("outro", "Outro"),
    )

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="interacoes")
    data_interacao = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default="ligacao",
        verbose_name="Tipo de Interação",
    )
    notas = models.TextField(verbose_name="Anotações")
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-data_interacao"]
        verbose_name = "Interação do Lead"
        verbose_name_plural = "Interações do Lead"

    def __str__(self):
        return f"Interação em {self.data_interacao.strftime('%d/%m/%Y')} para {self.lead.nome_interessado}"
