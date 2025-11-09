from django.contrib import admin
from .models import Lead, InteracaoLead
from django.contrib.auth import get_user_model


class InteracaoLeadInline(admin.TabularInline):
    model = InteracaoLead
    extra = 1

    readonly_fields = ("data_interacao",)
    fields = ("tipo", "notas", "responsavel", "data_interacao")
    autocomplete_fields = ["responsavel"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        User = get_user_model()
        if db_field.name == "responsavel":
            kwargs["queryset"] = User.objects.filter(tipo__in=["admin", "comercial"])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "nome_interessado",
        "status",
        "criado_por",
        "convertido_por",
        "curso_interesse",
        "data_criacao",
    )
    list_filter = (
        "status",
        "fonte",
        "curso_interesse",
        "data_criacao",
        "unidade_negocio",
        "criado_por",
        "convertido_por",
    )
    search_fields = (
        "nome_interessado",
        "nome_responsavel",
        "contato",
        "criado_por__username",
        "convertido_por__username",
    )
    list_per_page = 25
    ordering = ("-data_criacao",)

    readonly_fields = ("data_criacao",)

    autocomplete_fields = (
        "aluno_convertido",
        "criado_por",
        "convertido_por",
    )

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
                "classes": ("collapse",),
                "fields": (
                    "proposito_estudo",
                    "objetivo_tocar",
                    "motivo_interesse_especifico",
                    "sobre_voce",
                ),
            },
        ),
        (
            "Rastreamento e Conversão",
            {
                "fields": (
                    "observacoes",
                    "unidade_negocio",
                    "aluno_convertido",
                    "criado_por",
                    "convertido_por",
                )
            },
        ),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        User = get_user_model()
        if db_field.name in ["criado_por", "convertido_por"]:
            kwargs["queryset"] = User.objects.filter(tipo__in=["admin", "comercial"])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)


@admin.register(InteracaoLead)
class InteracaoLeadAdmin(admin.ModelAdmin):
    list_display = (
        "lead",
        "tipo",
        "responsavel",
        "data_interacao",
    )
    list_filter = ("tipo", "data_interacao", "responsavel")
    search_fields = ("lead__nome_interessado", "notas")
    autocomplete_fields = ["lead", "responsavel"]

    readonly_fields = ("data_interacao",)
    fields = ("lead", "tipo", "notas", "responsavel", "data_interacao")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        User = get_user_model()
        if db_field.name == "responsavel":
            kwargs["queryset"] = User.objects.filter(tipo__in=["admin", "comercial"])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
