from django.db import models
from django.conf import settings
from core.models import UnidadeNegocio
from scheduler.models import Aluno


def get_escola_unidade_negocio():
    """
    Busca e retorna a instância de UnidadeNegocio "Escola".
    Retorna None se não encontrar, para que o Django possa lidar com o erro.
    """
    try:
        # Tente buscar pelo nome exato. Mude 'Escola' se o nome no seu DB for diferente.
        return UnidadeNegocio.objects.get(nome="Escola")
    except UnidadeNegocio.DoesNotExist:
        return None


class Lead(models.Model):
    STATUS_CHOICES = (
        ("novo", "Novo"),
        ("em_contato", "Em Contato"),
        ("negociando", "Negociando"),
        ("convertido", "Convertido"),
        ("perdido", "Perdido"),
    )

    # Dados do Lead
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
    CURSO_CHOICES = (
        ('bateria', 'Bateria'),
        ('percussao', 'Percussão'),
        ('musicalizacao', 'Musicalização Infantil'),
        ('outro', 'Outro'),
    )
    NIVEL_CHOICES = (
        ('iniciante', 'Iniciante (nunca toquei)'),
        ('basico', 'Básico (já tive algum contato)'),
        ('intermediario', 'Intermediário (toco por hobby)'),
        ('avancado', 'Avançado (busco aperfeiçoamento)'),
    )
    HORARIO_CHOICES = (
        ('manha', 'Manhã (08:00 - 12:00)'),
        ('tarde', 'Tarde (14:00 - 17:00)'),
        ('noite', 'Noite (18:00 - 21:00)'),
    )

    curso_interesse = models.CharField(
        max_length=50, choices=CURSO_CHOICES, blank=True, null=True, verbose_name="Curso de Interesse"
    )
    nivel_experiencia = models.CharField(
        max_length=50, choices=NIVEL_CHOICES, blank=True, null=True, verbose_name="Nível de Experiência"
    )
    melhor_horario_contato = models.CharField(
        max_length=50, choices=HORARIO_CHOICES, blank=True, null=True, verbose_name="Melhor Horário para Contato"
    )
    observacoes = models.TextField(
        blank=True, null=True, verbose_name="Observações e Histórico"
    )

    # Dados de Controle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="novo")
    data_criacao = models.DateTimeField(auto_now_add=True)
    unidade_negocio = models.ForeignKey(
        UnidadeNegocio, on_delete=models.PROTECT, default=get_escola_unidade_negocio
    )

    # --- A PEÇA CHAVE PARA A CONVERSÃO ---
    aluno_convertido = models.OneToOneField(
        Aluno,
        on_delete=models.SET_NULL,  # Se o aluno for deletado, mantemos o lead
        null=True,
        blank=True,
        related_name="lead_origem",
    )

    def __str__(self):
        return self.nome_interessado


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
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["-data_interacao"]  # Ordena da mais recente para a mais antiga
        verbose_name = "Interação do Lead"
        verbose_name_plural = "Interações do Lead"

    def __str__(self):
        return f"Interação em {self.data_interacao.strftime('%d/%m/%Y')} para {self.lead.nome_interessado}"
