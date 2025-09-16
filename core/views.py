from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from .models import Notificacao
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict


def set_unidade_negocio(request, pk):
    request.session["unidade_ativa_id"] = pk

    referer_url = request.META.get("HTTP_REFERER", reverse("scheduler:dashboard"))
    return HttpResponseRedirect(referer_url)


@login_required
def marcar_notificacoes_como_lidas(request):
    if request.method == "POST":
        request.user.notificacoes.filter(lida=False).update(lida=True)
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)


@require_POST
@login_required
def marcar_notificacao_nao_lida(request, pk):
    notificacao = get_object_or_404(Notificacao, pk=pk, usuario=request.user)
    notificacao.lida = False
    notificacao.save()
    return JsonResponse({'status': 'success'})


@require_POST
@login_required
def excluir_notificacao(request, pk):
    notificacao = get_object_or_404(Notificacao, pk=pk, usuario=request.user)
    notificacao.delete()
    return JsonResponse({'status': 'success'})


@login_required
def notificacao_list_view(request):
    """
    Exibe uma lista de todas as notificações do usuário,
    com filtros e agrupamento por data.
    """
    # --- NOVO DICIONÁRIO DE TRADUÇÃO DOS MESES ---
    MESES_PT_COMPLETO = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
    }
    
    filtro_ativo = request.GET.get('filtro', 'todas') # Padrão para 'todas'
    
    base_queryset = request.user.notificacoes.all()

    if filtro_ativo == 'nao_lidas':
        base_queryset = base_queryset.filter(lida=False)

    grouped_notifications = defaultdict(list)
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    for notificacao in base_queryset:
        n_date = notificacao.data_criacao.date()
        if n_date == today:
            group_key = 'Hoje'
        elif n_date == yesterday:
            group_key = 'Ontem'
        elif today.year == n_date.year and today.month == n_date.month:
            group_key = 'Este Mês'
        else:
            # --- LÓGICA DE AGRUPAMENTO ALTERADA ---
            # Usa o dicionário para pegar o nome do mês em português
            nome_mes = MESES_PT_COMPLETO[n_date.month]
            group_key = f"{nome_mes} de {n_date.year}"

        grouped_notifications[group_key].append(notificacao)
    
    context = {
        'grouped_notifications': dict(grouped_notifications),
        'filtro_ativo': filtro_ativo,
    }
    return render(request, 'core/notificacao_list.html', context)
