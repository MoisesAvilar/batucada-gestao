from django.contrib import admin
from .models import Lead, InteracaoLead


# Define a exibição inline das interações dentro da página do Lead
class InteracaoLeadInline(admin.TabularInline):
    model = InteracaoLead
    extra = 1  # Quantos formulários em branco mostrar
    readonly_fields = ("data_interacao", "responsavel")
    fields = ("tipo", "notas", "data_interacao", "responsavel")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo Lead.
    """

    list_display = (
        "nome_interessado",
        "status",
        "curso_interesse",
        "contato",
        "data_criacao",
        "unidade_negocio",
    )
    list_filter = (
        "status",
        "fonte",
        "curso_interesse",
        "data_criacao",
        "unidade_negocio",
    )
    search_fields = (
        "nome_interessado",
        "nome_responsavel",
        "contato",
    )
    list_per_page = 25
    ordering = ("-data_criacao",)

    # Adiciona as interações diretamente na página de detalhes do Lead
    inlines = [InteracaoLeadInline]

    fieldsets = (
        (
            "Informações Principais",
            {
                "fields": (
                    "nome_interessado",
                    "nome_responsavel",
                    "contato",
                    "idade",
                    "data_criacao",
                )
            },
        ),
        (
            "Status e Qualificação",
            {
                "fields": (
                    "status",
                    "fonte",
                    "curso_interesse",
                    "nivel_experiencia",
                    "melhor_horario_contato",
                )
            },
        ),
        (
            "Detalhes Adicionais (Formulário)",
            {
                "classes": ("collapse",),  # Começa recolhido
                "fields": (
                    "proposito_estudo",
                    "objetivo_tocar",
                    "motivo_interesse_especifico",
                    "sobre_voce",
                ),
            },
        ),
        ("Outros", {"fields": ("observacoes", "unidade_negocio", "aluno_convertido")}),
    )

    def save_model(self, request, obj, form, change):
        # Associa o responsável ao salvar uma interação inline
        super().save_model(request, obj, form, change)
        for inline_formset in form.inline_formsets:
            for inline_form in inline_formset:
                if inline_form.instance.pk is None and not hasattr(
                    inline_form.instance, "responsavel"
                ):
                    if inline_form.has_changed():
                        inline_form.instance.responsavel = request.user
                        inline_form.instance.save()


@admin.register(InteracaoLead)
class InteracaoLeadAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo InteracaoLead.
    """

    list_display = (
        "lead",
        "tipo",
        "responsavel",
        "data_interacao",
    )
    list_filter = ("tipo", "data_interacao", "responsavel")
    search_fields = ("lead__nome_interessado", "notas")
    autocomplete_fields = ["lead"]  # Facilita a busca por um lead
