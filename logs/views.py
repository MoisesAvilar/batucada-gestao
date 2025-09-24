from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import AuditLog
from django.contrib.auth.decorators import login_required


@login_required
def logs_page(request):
    """Página de logs"""
    actions_info = [
        {"action": "criou", "label": "Criou", "color": "success"},
        {"action": "atualizou", "label": "Atualizou", "color": "warning"},
        {"action": "deletou", "label": "Deletou", "color": "danger"},
        {"action": "get", "label": "Acessou", "color": "primary"},
    ]
    return render(request, "logs/logs_page.html", {"actions_info": actions_info})


@login_required
def logs_api(request):
    """API de logs para datatables ou fetch JS"""
    days = int(request.GET.get("days", 30))
    start_date = timezone.now() - timedelta(days=days - 1)

    logs_qs = AuditLog.objects.filter(timestamp__gte=start_date).order_by("-timestamp")
    logs = []
    for log in logs_qs:
        # Renderiza resource_name diretamente
        resource_name = getattr(log, "resource_name", log.resource_type)

        # Se detail for dicionário, renderiza como string legível
        detail = log.detail
        if isinstance(detail, dict):
            detail_str = "<br>".join(
                f"{k}: {v}" for k, v in detail.items() if not k.startswith("_")
            )
        else:
            detail_str = str(detail)

        logs.append(
            {
                "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M"),
                "username": log.username
                or (log.user.get_full_name() if log.user else "anon"),
                "action": log.action.lower(),
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "resource_name": resource_name,
                "detail": detail_str,
                "method": log.method or "-",
                "ip_address": log.ip_address or "-",
                "tags": log.tags or "",
            }
        )

    return JsonResponse({"logs": logs})
