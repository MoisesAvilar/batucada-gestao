from django.contrib import admin
from .models import Lead, InteracaoLead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    # Colunas que aparecem na lista
    list_display = (
        "nome_interessado",
        "contato",
        "fonte",
        "curso_interesse",
        "melhor_horario_contato",
        "status",
        "criado_por",
        "data_criacao",
    )

    # Filtros da barra lateral
    list_filter = (
        "status",
        "fonte",
        "curso_interesse",
        "melhor_horario_contato",
        "data_criacao",
    )

    # Campos de busca
    search_fields = (
        "nome_interessado",
        "contato",
        "nome_responsavel",
        "fonte",
        "observacoes",
    )

    readonly_fields = (
        "data_criacao",
        # "criado_por",
        # "convertido_por",
        # "aluno_convertido",
    )

    # Organização visual do formulário de edição
    fieldsets = (
        (
            "Dados do Lead",
            {"fields": ("nome_interessado", "nome_responsavel", "contato", "idade")},
        ),
        (
            "Interesse e Origem",
            {
                "fields": (
                    "curso_interesse",
                    "melhor_horario_contato",
                    "nivel_experiencia",
                    "fonte",
                )
            },
        ),
        (
            "Detalhes",
            {
                "fields": (
                    "observacoes",
                    # "proposito_estudo",
                    # "objetivo_tocar",
                    # "motivo_interesse_especifico",
                    # "sobre_voce",
                )
            },
        ),
        (
            "Controle Interno",
            {
                "fields": (
                    "status",
                    "criado_por",
                    "convertido_por",
                    "aluno_convertido",
                    "data_criacao",
                )
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.criado_por:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(InteracaoLead)
class InteracaoLeadAdmin(admin.ModelAdmin):
    list_display = ("lead", "tipo", "responsavel", "data_interacao")
    list_filter = ("tipo", "data_interacao")
    search_fields = ("lead__nome_interessado", "notas")
    readonly_fields = ("data_interacao",)
