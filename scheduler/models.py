from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone


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
    data_criacao = models.DateField(
        default=timezone.now, 
        verbose_name="Data de Criação/Matrícula"
    )

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

    # --- CORRIGIDO ---
    alunos = models.ManyToManyField(
        "Aluno",
        blank=True,
        verbose_name="Alunos",
        related_name="aulas_aluno"
    )

    # --- CORRIGIDO ---
    professores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        limit_choices_to={"tipo__in": ["admin", "professor"]},
        verbose_name="Professores Atribuídos",
        related_name="aulas_lecionadas"
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
        nomes_alunos = ", ".join([aluno.nome_completo.title() for aluno in self.alunos.all()])
        if not nomes_alunos:
            if hasattr(self, 'modalidade') and self.modalidade.nome == "Atividade Complementar":
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
        if self.status != 'Realizada' or not hasattr(self, 'relatorioaula'):
            return False
        
        professor_validou = self.relatorioaula.professor_que_validou
        if not professor_validou:
            return False
            
        # Retorna True se o professor que validou NÃO EXISTE na lista de professores atribuídos.
        return not self.professores.filter(pk=professor_validou.pk).exists()


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
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        # A lógica para obter o nome do aluno foi ajustada
        primeiro_aluno = self.aula.alunos.first()
        nome_aluno_str = primeiro_aluno.nome_completo if primeiro_aluno else "N/A"
        return f"Relatório da aula de {nome_aluno_str} em {self.aula.data_hora.strftime('%d/%m/%Y')}"


# --- NOVOS MODELOS PARA OS ITENS DINÂMICOS ---
class ItemRudimento(models.Model):
    """ Armazena um único exercício de rudimento associado a um relatório. """
    relatorio = models.ForeignKey(RelatorioAula, related_name='itens_rudimentos', on_delete=models.CASCADE)
    descricao = models.CharField(max_length=255, verbose_name="Exercício")
    bpm = models.CharField(max_length=50, blank=True, null=True, verbose_name="BPM")
    duracao_min = models.IntegerField(verbose_name="Duração (min)", null=True, blank=True)
    observacoes = models.TextField(verbose_name="Observações", blank=True, null=True)

    def __str__(self):
        return f"Rudimento: {self.descricao} para {self.relatorio}"


class ItemRitmo(models.Model):
    """ Armazena um único exercício de ritmo associado a um relatório. """
    relatorio = models.ForeignKey(RelatorioAula, related_name='itens_ritmo', on_delete=models.CASCADE)
    descricao = models.CharField(max_length=255, verbose_name="Exercício")
    livro_metodo = models.CharField(max_length=200, blank=True, null=True, verbose_name="Livro/Método")
    bpm = models.CharField(max_length=50, blank=True, null=True, verbose_name="Clique/BPM")
    duracao_min = models.IntegerField(verbose_name="Duração (min)", null=True, blank=True)
    observacoes = models.TextField(verbose_name="Observações", blank=True, null=True)

    def __str__(self):
        return f"Ritmo: {self.descricao} para {self.relatorio}"


class ItemVirada(models.Model):
    """ Armazena um único exercício de virada associado a um relatório. """
    relatorio = models.ForeignKey(RelatorioAula, related_name='itens_viradas', on_delete=models.CASCADE)
    descricao = models.CharField(max_length=255, verbose_name="Exercício")
    bpm = models.CharField(max_length=50, blank=True, null=True, verbose_name="Clique/BPM")
    duracao_min = models.IntegerField(verbose_name="Duração (min)", null=True, blank=True)
    observacoes = models.TextField(verbose_name="Observações", blank=True, null=True)

    def __str__(self):
        return f"Virada: {self.descricao} para {self.relatorio}"


class PresencaAluno(models.Model):
    STATUS_CHOICES = (
        ('presente', 'Presente'),
        ('ausente', 'Ausente'),
    )
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE, related_name="presencas")
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='presente')

    class Meta:
        # Garante que um aluno não pode ter dois status de presença para a mesma aula
        unique_together = ('aula', 'aluno')

    def __str__(self):
        return f"{self.aluno.nome_completo} - {self.get_status_display()} em {self.aula}"


class PresencaProfessor(models.Model):
    STATUS_CHOICES = (
        ('presente', 'Presente'),
        ('ausente', 'Ausente'),
    )
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE, related_name="presencas_professores")
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='presencas_registradas' # Nome explícito para a relação
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='presente')

    class Meta:
        unique_together = ('aula', 'professor')

    def __str__(self):
        return f"{self.professor.username} - {self.get_status_display()} em {self.aula}"
