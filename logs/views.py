import json
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from .models import AuditLog
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required


@login_required
def logs_page(request):
    """Página de logs com filtros e paginação."""
    actions_info = [
        {"action": "criou", "label": "Criou", "color": "success"},
        {"action": "atualizou", "label": "Atualizou", "color": "warning"},
        {"action": "deletou", "label": "Deletou", "color": "danger"},
        {"action": "get", "label": "Acessou", "color": "primary"},
    ]

    days = int(request.GET.get("days", 30))
    username_filter = request.GET.get("username", "")
    resource_filter = request.GET.get("resource", "")
    tags_filter = request.GET.get("tags", "")
    page = int(request.GET.get("page", 1))

    start_date = timezone.now() - timedelta(days=days)

    logs_qs = AuditLog.objects.filter(timestamp__gte=start_date).order_by("-timestamp")

    if username_filter:
        logs_qs = logs_qs.filter(username__icontains=username_filter)
    if resource_filter:
        logs_qs = logs_qs.filter(resource_name__icontains=resource_filter)
    if tags_filter:
        logs_qs = logs_qs.filter(tags__icontains=tags_filter)

    paginator = Paginator(logs_qs, 100)
    page_obj = paginator.get_page(page)

    logs = []
    for log in page_obj:
        print("LOG DETAIL RAW:", log.detail)
        # Converter timestamp para timezone local antes de formatar
        local_timestamp = timezone.localtime(log.timestamp) if log.timestamp else None

        detail_str = str(log.detail)
        detail_json = ""
        if isinstance(log.detail, dict):
            # JSON formatado para mostrar bonitinho
            detail_json = json.dumps(log.detail, indent=2, ensure_ascii=False)
            detail_str = "\n".join(f"{k}: {v}" for k, v in log.detail.items())
        else:
            # Se for string ou outro tipo, tenta exibir direto
            detail_json = json.dumps(log.detail, indent=2, ensure_ascii=False)

        logs.append({
            "id": log.pk,
            # Use local_timestamp aqui, formate com strftime para o padrão BR
            "timestamp": local_timestamp.strftime("%d/%m/%Y %H:%M") if local_timestamp else "",
            "username": log.username or (log.user.get_full_name() if log.user else "anon"),
            "action": log.action.lower(),
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "resource_name": log.resource_name,
            "detail": log.detail,
            "detail_str": detail_str,
            "detail_json": detail_json,
            "method": log.method or "-",
            "ip_address": log.ip_address or "-",
            "tags": log.tags or "",
        })

    logs_json = json.dumps(logs, cls=DjangoJSONEncoder)

    context = {
        "actions_info": actions_info,
        "logs": logs,
        "page_obj": page_obj,
        "filters": {
            "days": days,
            "username": username_filter,
            "resource": resource_filter,
            "tags": tags_filter,
        },
        "logs_json": logs_json,
    }
    return render(request, "logs/logs_page.html", context)


@login_required
def logs_api(request):
    """API de logs com suporte a filtros e paginação."""
    days = int(request.GET.get("days", 30))
    start_date = timezone.now() - timedelta(days=days)

    username_filter = request.GET.get("username", "")
    resource_filter = request.GET.get("resource", "")
    tags_filter = request.GET.get("tags", "")
    page = int(request.GET.get("page", 1))
    per_page = 100

    logs_qs = AuditLog.objects.filter(timestamp__gte=start_date).order_by("-timestamp")

    if username_filter:
        logs_qs = logs_qs.filter(username__icontains=username_filter)
    if resource_filter:
        logs_qs = logs_qs.filter(resource_name__icontains=resource_filter)
    if tags_filter:
        logs_qs = logs_qs.filter(tags__icontains=tags_filter)

    paginator = Paginator(logs_qs, per_page)
    page_obj = paginator.get_page(page)

    logs = []
    for log in page_obj:
        local_timestamp = timezone.localtime(log.timestamp) if log.timestamp else None

        if isinstance(log.detail, dict) and log.detail:
            detail_str = "\n".join(f"{k}: {v}" for k, v in log.detail.items())
        else:
            detail_str = "Sem detalhes disponíveis."

        logs.append({
            "id": log.pk,
            "timestamp": local_timestamp.strftime("%d/%m/%Y %H:%M") if local_timestamp else "",
            "username": log.username or (log.user.get_full_name() if log.user else "anon"),
            "action": log.action.lower(),
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "resource_name": log.resource_name,
            "detail": log.detail,
            "detail_str": detail_str,
            "method": log.method or "-",
            "ip_address": log.ip_address or "-",
            "tags": log.tags or "",
        })

    return JsonResponse({
        "logs": logs,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
        "page": page_obj.number,
        "num_pages": paginator.num_pages,
        "total": paginator.count,
    })
