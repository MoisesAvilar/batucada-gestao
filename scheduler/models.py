from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal


class CustomUser(AbstractUser):
    TIPO_USUARIO_CHOICES = (
        ("admin", "Administrador"),
        ("professor", "Professor"),
        ("comercial", "Comercial"),
    )
    tipo = models.CharField(
        max_length=15,
        choices=TIPO_USUARIO_CHOICES,
        default="professor",
        verbose_name="Tipo de Usuário",
    )
    profile_picture_url = models.URLField(
        max_length=500, blank=True, null=True, verbose_name="URL da Foto de Perfil"
    )

    def __str__(self):
        return f"{self.username}"

    class Meta:
        ordering = ['username']


class Aluno(models.Model):
    STATUS_CHOICES = (
        ("ativo", "Ativo"),
        ("inativo", "Inativo"),
        ("trancado", "Trancado"),
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="ativo", verbose_name="Status"
    )
    nome_completo = models.CharField(max_length=255, verbose_name="Nome Completo")
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    valor_mensalidade = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Valor da Mensalidade",
    )
    dia_vencimento = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Dia do Vencimento",
        help_text="Dia do mês para o vencimento da mensalidade (ex: 5, 10, 15).",
    )
    data_criacao = models.DateField(
        default=timezone.now, verbose_name="Data de Criação/Matrícula"
    )
    cpf = models.CharField(
        max_length=14, unique=True, null=True, blank=True, verbose_name="CPF"
    )
    responsavel_nome = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Nome do Responsável",
        help_text="Preencher caso o aluno seja menor de idade.",
    )

    def get_status_pagamento(self):
        # Se o aluno não for mensalista, ele está sempre 'N/A'
        if not self.valor_mensalidade or not self.dia_vencimento:
            return {"status": "N/A", "cor": "secondary"}

        hoje = timezone.now().date()
        mes_atual = hoje.month
        ano_atual = hoje.year

        # Verifica se já existe um pagamento de mensalidade neste mês
        pagamento_mes = self.financial_transactions.filter(
            category__type="income",
            transaction_date__year=ano_atual,
            transaction_date__month=mes_atual,
            # Consideramos pago se o valor for igual ou maior que a mensalidade
            amount__gte=self.valor_mensalidade,
        ).exists()

        if pagamento_mes:
            return {"status": "Em Dia", "cor": "success"}

        # Se não pagou, vamos verificar o vencimento
        data_vencimento = hoje.replace(day=self.dia_vencimento)

        if hoje > data_vencimento:
            return {"status": "Em Atraso", "cor": "danger"}

        # Verifica se faltam 5 dias ou menos para o vencimento
        if (data_vencimento - hoje).days <= 5:
            return {"status": "Próximo Venc.", "cor": "warning"}

        # Se nenhuma das condições acima for atendida, o pagamento está em aberto mas não próximo do vencimento
        return {"status": "Aguardando Pag.", "cor": "info"}
    
    def get_absolute_url(self):
        return reverse("scheduler:detalhe_aluno", kwargs={"pk": self.pk})

    def __str__(self):
        return self.nome_completo


class Modalidade(models.Model):
    TIPO_PAGAMENTO_CHOICES = (
        ('aula', 'Por Aula (Valor Fixo)'),
        ('aluno', 'Por Aluno (Valor por Presença)'),
    )

    nome = models.CharField(max_length=100, unique=True)
    
    valor_pagamento_professor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Valor do Pagamento por Aula/Aluno",
        help_text="Valor padrão pago ao professor."
    )
    tipo_pagamento = models.CharField(
        max_length=10,
        choices=TIPO_PAGAMENTO_CHOICES,
        default='aula',
        verbose_name="Método de Cálculo do Pagamento",
        help_text="Define se o pagamento é um valor fixo por aula ou multiplicado pelo número de alunos presentes."
    )

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Aula(models.Model):
    STATUS_AULA_CHOICES = (
        ("Agendada", "Agendada"),
        ("Realizada", "Realizada"),
        ("Cancelada", "Cancelada"),
        ("Aluno Ausente", "Aluno Ausente"),
        ("Reposta", "Reposta"),
    )

    # --- CORRIGIDO ---
    alunos = models.ManyToManyField(
        "Aluno", blank=True, verbose_name="Alunos", related_name="aulas_aluno"
    )

    # --- CORRIGIDO ---
    professores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        limit_choices_to={"tipo__in": ["admin", "professor"]},
        verbose_name="Professores Atribuídos",
        related_name="aulas_lecionadas",
    )

    modalidade = models.ForeignKey(
        Modalidade, on_delete=models.PROTECT, verbose_name="Modalidade"
    )
    data_hora = models.DateTimeField(verbose_name="Data e Horário")
    status = models.CharField(
        max_length=20, choices=STATUS_AULA_CHOICES, default="Agendada"
    )

    def __str__(self):
        # This method is now consistent with the field name 'alunos'
        nomes_alunos = ", ".join(
            [aluno.nome_completo.title() for aluno in self.alunos.all()]
        )
        if not nomes_alunos:
            if (
                hasattr(self, "modalidade")
                and self.modalidade.nome == "Atividade Complementar"
            ):
                return f"Atividade Complementar em {self.data_hora.strftime('%d/%m/%Y %H:%M')}"
            return f"{getattr(self, 'modalidade', 'Aula')} (sem alunos) em {self.data_hora.strftime('%d/%m/%Y %H:%M')}"
        return f"{self.modalidade.nome} com {nomes_alunos} em {self.data_hora.strftime('%d/%m/%Y %H:%M')}"

    @property
    def foi_substituida(self):
        """
        Verifica se a aula foi realizada por um professor que não estava
        na lista original de professores atribuídos. IGNORA Atividades Complementares.
        """
        # --- NOVA VERIFICAÇÃO ---
        # Se for uma AC, nunca é uma substituição.
        if "atividade complementar" in self.modalidade.nome.lower():
            return False

        # Se a aula não foi 'Realizada' ou não tem relatório, não pode ter sido substituída.
        if self.status != "Realizada" or not hasattr(self, "relatorioaula"):
            return False

        professor_validou = self.relatorioaula.professor_que_validou
        if not professor_validou:
            return False

        # Retorna True se o professor que validou NÃO EXISTE na lista de professores atribuídos.
        return not self.professores.filter(pk=professor_validou.pk).exists()
    
    def clean(self):
        super().clean()
        # Esta validação é feita após o objeto ter um ID (self.pk),
        # pois campos ManyToMany só podem ser alterados depois do primeiro save.
        if self.pk:
            # Regra 1: Não permitir aula sem professor
            if self.professores.count() == 0:
                raise ValidationError(
                    'Não é possível salvar uma aula sem ao menos um professor associado.'
                )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        if not is_new:
            old_status = (
                Aula.objects.filter(pk=self.pk).values_list("status", flat=True).first()
            )

        super().save(*args, **kwargs)

        if self.status == "Aluno Ausente" and old_status != "Aluno Ausente":
            from .models import PresencaAluno

            for aluno in self.alunos.all():
                presenca, created = PresencaAluno.objects.get_or_create(
                    aula=self, aluno=aluno
                )
                presenca.status = "ausente"
                presenca.save()


class RelatorioAula(models.Model):
    # Campos que permanecem pois são únicos por relatório
    aula = models.OneToOneField(Aula, on_delete=models.CASCADE, primary_key=True)
    conteudo_teorico = models.TextField(
        verbose_name="Conteúdo Teórico Abordado", blank=True, null=True
    )

    observacoes_teoria = models.TextField(
        verbose_name="Observações sobre a Teoria", blank=True, null=True
    )

    repertorio_musicas = models.TextField(
        verbose_name="Músicas do Repertório", blank=True, null=True
    )

    observacoes_repertorio = models.TextField(
        verbose_name="Observações sobre o Repertório", blank=True, null=True
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
    ultimo_editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="relatorios_editados",
        verbose_name="Última Edição Por"
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        # A lógica para obter o nome do aluno foi ajustada
        primeiro_aluno = self.aula.alunos.first()
        nome_aluno_str = primeiro_aluno.nome_completo if primeiro_aluno else "N/A"
        return f"Relatório da aula de {nome_aluno_str} em {self.aula.data_hora.strftime('%d/%m/%Y')}"


# --- NOVOS MODELOS PARA OS ITENS DINÂMICOS ---
class ItemRudimento(models.Model):
    """Armazena um único exercício de rudimento associado a um relatório."""

    relatorio = models.ForeignKey(
        RelatorioAula, related_name="itens_rudimentos", on_delete=models.CASCADE
    )
    descricao = models.CharField(max_length=255, verbose_name="Exercício")
    bpm = models.CharField(max_length=50, blank=True, null=True, verbose_name="BPM")
    duracao_min = models.IntegerField(
        verbose_name="Duração (min)", null=True, blank=True
    )
    observacoes = models.TextField(verbose_name="Observações", blank=True, null=True)

    def __str__(self):
        return f"Rudimento: {self.descricao} para {self.relatorio}"


class ItemRitmo(models.Model):
    """Armazena um único exercício de ritmo associado a um relatório."""

    relatorio = models.ForeignKey(
        RelatorioAula, related_name="itens_ritmo", on_delete=models.CASCADE
    )
    descricao = models.CharField(max_length=255, verbose_name="Exercício")
    livro_metodo = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Livro/Método"
    )
    bpm = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Clique/BPM"
    )
    duracao_min = models.IntegerField(
        verbose_name="Duração (min)", null=True, blank=True
    )
    observacoes = models.TextField(verbose_name="Observações", blank=True, null=True)

    def __str__(self):
        return f"Ritmo: {self.descricao} para {self.relatorio}"


class ItemVirada(models.Model):
    """Armazena um único exercício de virada associado a um relatório."""

    relatorio = models.ForeignKey(
        RelatorioAula, related_name="itens_viradas", on_delete=models.CASCADE
    )
    descricao = models.CharField(max_length=255, verbose_name="Exercício")
    bpm = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Clique/BPM"
    )
    duracao_min = models.IntegerField(
        verbose_name="Duração (min)", null=True, blank=True
    )
    observacoes = models.TextField(verbose_name="Observações", blank=True, null=True)

    def __str__(self):
        return f"Virada: {self.descricao} para {self.relatorio}"


class PresencaAluno(models.Model):
    STATUS_CHOICES = (
        ("presente", "Presente"),
        ("ausente", "Ausente"),
    )
    TIPO_FALTA_CHOICES = (
        ('injustificada', 'Injustificada'),
        ('justificada', 'Justificada'),
    )
    tipo_falta = models.CharField(
        max_length=15, 
        choices=TIPO_FALTA_CHOICES, 
        default='injustificada',
        blank=True,
        null=True,
        verbose_name="Tipo de Falta"
    )

    aula_reposicao = models.OneToOneField(
        'Aula', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='aula_reposta_de',
        verbose_name="Aula de Reposição Agendada"
    )
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE, related_name="presencas")
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="presente")

    class Meta:
        # Garante que um aluno não pode ter dois status de presença para a mesma aula
        unique_together = ("aula", "aluno")

    def __str__(self):
        return (
            f"{self.aluno.nome_completo} - {self.get_status_display()} em {self.aula}"
        )


class PresencaProfessor(models.Model):
    STATUS_CHOICES = (
        ("presente", "Presente"),
        ("ausente", "Ausente"),
    )
    aula = models.ForeignKey(
        Aula, on_delete=models.CASCADE, related_name="presencas_professores"
    )
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="presencas_registradas",  # Nome explícito para a relação
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="presente")

    class Meta:
        unique_together = ("aula", "professor")

    def __str__(self):
        return f"{self.professor.username} - {self.get_status_display()} em {self.aula}"


class TourVisto(models.Model):
    """Registra que um usuário específico já visualizou um determinado tour."""
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="tours_vistos")
    tour_id = models.CharField(max_length=100, help_text="Um identificador único para o tour, ex: 'horarios_fixos_v1'")
    data_visualizacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'tour_id')

    def __str__(self):
        return f"{self.usuario.username} viu o tour {self.tour_id}"
