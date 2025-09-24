# scheduler/admin.py

from django.contrib import admin
from django.db.models import Count
from .models import (
    Aula,
    Aluno,
    Modalidade,
    CustomUser,
    RelatorioAula,
    ItemRudimento,
    ItemRitmo,
    ItemVirada,
    TourVisto
)


# Registros de outros modelos (sem alteração)
@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = (
        "status",
        "nome_completo",
        "email",
        "cpf",
        "responsavel_nome",
        "valor_mensalidade",
        "dia_vencimento",
    )
    search_fields = ("nome_completo", "email", "cpf", "responsavel_nome")
    ordering = ("nome_completo",)
    fieldsets = (
        (
            "Informações Pessoais",
            {
                "fields": (
                    "status",
                    "nome_completo",
                    "email",
                    "telefone",
                    "cpf",
                    "responsavel_nome",
                    "data_criacao",
                )
            },
        ),
        (
            "Detalhes Financeiros (Mensalistas)",
            {
                "classes": ("collapse",),
                "fields": ("valor_mensalidade", "dia_vencimento"),
                "description": "Preencha estes campos apenas para alunos com pagamento mensal recorrente.",
            },
        ),
    )


@admin.register(Modalidade)
class ModalidadeAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


class ItemRudimentoInline(admin.TabularInline):
    model = ItemRudimento
    extra = 1


class ItemRitmoInline(admin.TabularInline):
    model = ItemRitmo
    extra = 1


class ItemViradaInline(admin.TabularInline):
    model = ItemVirada
    extra = 1


@admin.register(RelatorioAula)
class RelatorioAulaAdmin(admin.ModelAdmin):
    # --- CAMPOS EXIBIDOS NA LISTA ---
    list_display = (
        "aula",
        "professor_que_validou",
        "get_aula_status",
        "data_atualizacao",
    )

    # --- FILTROS ADICIONADOS NA BARRA LATERAL ---
    list_filter = (
        ("data_atualizacao", admin.DateFieldListFilter),
        "professor_que_validou",  # Filtra pelo professor que preencheu o relatório
        "aula__professores",  # <-- NOVO FILTRO ADICIONADO AQUI
        "aula__modalidade",
        "aula__status",
    )

    # --- CAMPO DE BUSCA ---
    search_fields = (
        "aula__alunos__nome_completo",
        "professor_que_validou__username",
        "aula__professores__username",  # Adicionado para buscar por professor atribuído
        "aula__modalidade__nome",
        "conteudo_teorico",
        "repertorio_musicas",
    )

    # --- O RESTO DA SUA CONFIGURAÇÃO ---
    autocomplete_fields = ("aula", "professor_que_validou")
    inlines = [ItemRudimentoInline, ItemRitmoInline, ItemViradaInline]
    list_per_page = 25

    # --- MÉTODO PARA EXIBIR O STATUS DA AULA NA LISTA ---
    @admin.display(description="Status da Aula", ordering="aula__status")
    def get_aula_status(self, obj):
        if obj.aula:
            return obj.aula.get_status_display()
        return "N/A"


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "first_name", "last_name", "tipo", "is_staff")
    list_filter = ("tipo", "is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)


# --- INÍCIO DAS MELHORIAS PARA RELATÓRIOS DE AULA ---

# 1. FILTROS PERSONALIZADOS (A MÁGICA ACONTECE AQUI)


class TamanhoTurmaFilter(admin.SimpleListFilter):
    """Filtra aulas entre individuais e em grupo."""

    title = "Tamanho da Turma"
    parameter_name = "tamanho_turma"

    def lookups(self, request, model_admin):
        return (
            ("individual", "Aula Individual"),
            ("grupo", "Aula em Grupo"),
        )

    def queryset(self, request, queryset):
        if self.value() == "individual":
            return queryset.filter(alunos_count=1)
        if self.value() == "grupo":
            return queryset.filter(alunos_count__gt=1)
        return queryset


class StatusRelatorioFilter(admin.SimpleListFilter):
    """Filtra aulas que possuem ou não um relatório preenchido."""

    title = "Status do Relatório"
    parameter_name = "status_relatorio"

    def lookups(self, request, model_admin):
        return (
            ("com_relatorio", "Com Relatório"),
            ("sem_relatorio", "Sem Relatório"),
        )

    def queryset(self, request, queryset):
        if self.value() == "com_relatorio":
            return queryset.filter(relatorioaula__isnull=False)
        if self.value() == "sem_relatorio":
            return queryset.filter(relatorioaula__isnull=True)
        return queryset


class SubstituicaoFilter(admin.SimpleListFilter):
    """Filtra aulas que foram substituições."""

    title = "Tipo de Aula"
    parameter_name = "tipo_aula"

    def lookups(self, request, model_admin):
        return (("substituicao", "Apenas Substituições"),)

    def queryset(self, request, queryset):
        if self.value() == "substituicao":
            # Filtra aulas onde o professor que validou não está na lista de atribuídos
            return queryset.filter(
                status="Realizada", relatorioaula__professor_que_validou__isnull=False
            ).exclude(professores=models.F("relatorioaula__professor_que_validou"))
        return queryset


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    """
    Configuração da área de admin para o modelo Aula, turbinada para relatórios.
    """

    # 2. MELHORAS NA EXIBIÇÃO DA LISTA
    list_display = (
        "data_hora",
        "modalidade",
        "get_alunos_display",
        "get_professores_atribuidos",
        "get_professor_que_realizou",
        "status",
        "foi_substituida_icon",  # Coluna com ícone para substituição
    )

    # 3. FILTROS (PADRÃO + PERSONALIZADOS)
    list_filter = (
        ("data_hora", admin.DateFieldListFilter),  # Filtro de data padrão do Django
        "status",
        "modalidade",
        TamanhoTurmaFilter,  # Nosso filtro customizado
        StatusRelatorioFilter,  # Nosso filtro customizado
        SubstituicaoFilter,  # Nosso filtro customizado
        "professores",  # Filtro padrão por professor atribuído
    )

    # 4. CAMPO DE BUSCA
    search_fields = (
        "alunos__nome_completo",
        "professores__username",
        "professores__first_name",
        "professores__last_name",
        "modalidade__nome",
        "relatorioaula__professor_que_validou__username",  # Buscar pelo professor que realizou
    )

    # 5. NAVEGAÇÃO POR HIERARQUIA DE DATA
    date_hierarchy = "data_hora"

    ordering = ("-data_hora",)
    list_per_page = 20  # Quantidade de itens por página
    autocomplete_fields = ("alunos", "professores")

    # 6. AÇÕES EM MASSA
    actions = ["marcar_como_cancelada"]

    @admin.action(description='Marcar aulas selecionadas como "Cancelada"')
    def marcar_como_cancelada(self, request, queryset):
        updated = queryset.update(status="Cancelada")
        self.message_user(request, f"{updated} aulas foram marcadas como canceladas.")

    # 7. MÉTODOS PARA MELHORAR A EXIBIÇÃO E PERFORMANCE
    def get_queryset(self, request):
        # Otimiza a consulta, pré-carregando dados e adicionando contagens
        queryset = super().get_queryset(request)
        queryset = (
            queryset.select_related(
                "modalidade", "relatorioaula__professor_que_validou"
            )
            .prefetch_related("alunos", "professores")
            .annotate(alunos_count=Count("alunos"))
        )
        return queryset

    # Métodos para `list_display`
    @admin.display(description="Alunos", ordering="alunos__nome_completo")
    def get_alunos_display(self, obj):
        return ", ".join([aluno.nome_completo.split()[0] for aluno in obj.alunos.all()])

    @admin.display(description="Prof. Atribuído(s)", ordering="professores__username")
    def get_professores_atribuidos(self, obj):
        return ", ".join([prof.username for prof in obj.professores.all()])

    @admin.display(
        description="Prof. que Realizou",
        ordering="relatorioaula__professor_que_validou__username",
    )
    def get_professor_que_realizou(self, obj):
        if (
            hasattr(obj, "relatorioaula")
            and obj.relatorioaula
            and obj.relatorioaula.professor_que_validou
        ):
            return obj.relatorioaula.professor_que_validou.username
        return "—"  # Retorna um traço se não houver relatório

    @admin.display(description="Subst.", boolean=True)
    def foi_substituida_icon(self, obj):
        # Usa a property que já existe no seu modelo!
        return obj.foi_substituida


@admin.register(TourVisto)
class TourVistoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tour_id", "data_visualizacao")
    list_filter = ("tour_id", "data_visualizacao")
    search_fields = ("usuario__username", "usuario__email", "tour_id")
    ordering = ("-data_visualizacao",)
    date_hierarchy = "data_visualizacao"
