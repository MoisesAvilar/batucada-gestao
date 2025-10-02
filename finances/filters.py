from django.contrib import admin


class AnoFilter(admin.SimpleListFilter):
    """Filtro de ano para modelos com campo de data."""

    title = "Ano"
    parameter_name = "ano"

    # Define os anos disponíveis dinamicamente
    def lookups(self, request, model_admin):
        # 'campo_data' deve existir no queryset do model
        campo_data = getattr(model_admin.model, "data_competencia", None)
        if not campo_data:
            return []
        anos = model_admin.model.objects.dates("data_competencia", "year")
        return [(ano.year, str(ano.year)) for ano in anos]

    # Filtra o queryset
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(data_competencia__year=self.value())
        return queryset
