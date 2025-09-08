from .models import AuditLog
from django.forms.models import model_to_dict


def log_action(
    request=None, instance=None, action="custom", detail_fields=None, tags=None
):
    """
    Cria um registro de AuditLog para qualquer modelo ou ação.

    Parâmetros:
    - request: HttpRequest (opcional, para pegar user, ip, user_agent, path, method)
    - instance: Modelo Django (opcional, se houver um registro relacionado)
    - action: string, ex: "Criou", "Atualizou", "Deletou"
    - detail_fields: lista de campos do modelo que devem entrar no detail dict
    - tags: string ou lista de tags
    """
    resource_type = instance._meta.model_name.title() if instance else "http"
    resource_id = str(instance.pk) if instance else ""
    resource_name = str(instance) if instance else ""

    # Montar o dict de detalhes
    detail = {}
    if instance and detail_fields:
        model_dict = model_to_dict(instance)
        for f in detail_fields:
            if f in model_dict:
                detail[f] = model_dict[f]

    # Metadata do request
    metadata = {}
    username = ""
    ip = ""
    ua = ""
    path = ""
    method = ""

    if request:
        username = (
            request.user.get_full_name()
            if getattr(request.user, "is_authenticated", False)
            else getattr(request.user, "username", "")
        )
        ip = request.META.get("REMOTE_ADDR") or request.META.get("HTTP_X_FORWARDED_FOR")
        ua = request.META.get("HTTP_USER_AGENT", "")[:1000]
        path = request.path
        method = request.method
        metadata = {
            "GET": dict(request.GET),
            "POST_keys": list(request.POST.keys()),
            "status_code": getattr(request, "status_code", 200),
        }

    # Normalizar tags
    if tags is None:
        tags = [resource_type.lower(), action.lower()]
    elif isinstance(tags, str):
        tags = [tags]

    AuditLog.objects.create(
        user=(
            request.user
            if request and getattr(request.user, "is_authenticated", False)
            else None
        ),
        username=username,
        ip_address=ip,
        user_agent=ua,
        path=path,
        method=method,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        detail=detail,
        metadata=metadata,
        tags=",".join(tags),
    )
