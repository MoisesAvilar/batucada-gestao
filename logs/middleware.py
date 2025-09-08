from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class AuditMiddleware(MiddlewareMixin):
    IGNORED_PATHS = ("/static/", "/media/", "/favicon.ico", "/health", "/admin/")
    _recent_gets = {}  # memória para ignorar GETs repetidos

    def process_response(self, request, response):
        try:
            if any(request.path.startswith(p) for p in self.IGNORED_PATHS):
                return response

            # Registrar apenas POST, PUT, PATCH, DELETE, GET "/" ou erros
            if (
                request.method in ("POST", "PUT", "PATCH", "DELETE")
                or (request.method == "GET" and request.path.endswith("/"))
                or response.status_code >= 400
            ):
                # --- Usuário ---
                user = getattr(request, "user", None)
                username = getattr(request, "audit_username", None)
                if not username:
                    if user and getattr(user, "is_authenticated", False):
                        username = user.get_full_name() or user.username
                    else:
                        username = "anon"

                ip = get_client_ip(request)
                ua = request.META.get("HTTP_USER_AGENT", "")[:1000]

                # --- Ignorar GET repetidos ---
                if request.method == "GET":
                    key = f"{ip}_{username}_{request.path}"
                    if self._recent_gets.get(key):
                        return response
                    self._recent_gets[key] = True

                # --- Dados do recurso ---
                resource_type = getattr(request, "audit_resource_type", "http")
                resource_id = str(getattr(request, "audit_resource_id", "")) or ""
                resource_name = getattr(request, "audit_resource_name", None) or ""
                detail = getattr(request, "audit_detail", {}) or {}
                tags = getattr(
                    request, "audit_tags", f"{resource_type},{request.method.lower()}"
                )

                # --- Definir ação amigável ---
                if request.method == "GET":
                    action = "visualizou"
                    if not resource_name:
                        resource_name = f"Página {request.path}"
                else:
                    action = getattr(request, "audit_action", request.method.lower())

                metadata = {
                    "GET": dict(request.GET),
                    "POST_keys": list(request.POST.keys()),
                    "status_code": response.status_code,
                }

                AuditLog.objects.create(
                    user=(
                        user
                        if (user and getattr(user, "is_authenticated", False))
                        else None
                    ),
                    username=username,
                    ip_address=ip,
                    user_agent=ua,
                    path=request.path,
                    method=request.method,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    resource_name=resource_name,
                    detail=detail,
                    metadata=metadata,
                    tags=tags,
                )
        except Exception as e:
            # opcional: logar em console para debug
            print("AuditMiddleware erro:", e)

        return response