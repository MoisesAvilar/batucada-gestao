from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum

class AnoMesFilter(SimpleListFilter):
    title = _("Ano / Mês")
    parameter_name = "ano_mes"

    def lookups(self, request, model_admin):
        qs = model_admin.model.objects.all()
        datas = qs.dates("data_competencia", "month", order="DESC")
        lookups = []

        anos = sorted({d.year for d in datas}, reverse=True)

        for ano in anos:
            meses = [d for d in datas if d.year == ano]
            for mes in meses:
                total = qs.filter(
                    data_competencia__year=mes.year,
                    data_competencia__month=mes.month
                ).aggregate(Sum("valor"))["valor__sum"] or 0
                lookups.append((
                    f"{mes.year}-{mes.month:02d}",
                    f"{mes.strftime('%m/%Y')} — R$ {total:,.2f}"
                ))
        return lookups

    def queryset(self, request, queryset):
        if self.value():
            ano, mes = self.value().split("-")
            return queryset.filter(
                data_competencia__year=ano,
                data_competencia__month=mes
            )
        return queryset
