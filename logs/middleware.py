from .request_util import set_current_request
from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class AuditMiddleware(MiddlewareMixin):
    IGNORED_PATHS = ("/static/", "/media/", "/favicon.ico", "/health", "/admin/")

    def process_response(self, request, response):
        try:
            # Ignora paths que não queremos logar
            if any(request.path.startswith(p) for p in self.IGNORED_PATHS):
                return response

            # Só registra GETs bem-sucedidos ou qualquer requisição com erro
            should_log = (request.method == "GET" and response.status_code < 400) or \
                         (response.status_code >= 400)

            if not should_log:
                return response

            user = getattr(request, "user", None)
            username = ""
            if user and getattr(user, "is_authenticated", False):
                username = user.get_full_name() or user.username
            else:
                username = "anon"
            
            ip = get_client_ip(request)

            # Para GET, definimos a ação como "visualizou"
            if request.method == "GET":
                action = "visualizou"
                resource_name = f"Página {request.path}"
                detail = {}
                if request.GET:
                    detail["query_params"] = dict(request.GET)
            else: # Para erros (status >= 400)
                action = f"erro_{response.status_code}"
                resource_name = f"Falha em {request.path}"
                detail = {
                    "reason_phrase": response.reason_phrase,
                    "method": request.method
                }

            AuditLog.objects.create(
                user=user if user and user.is_authenticated else None,
                username=username,
                ip_address=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
                path=request.path,
                method=request.method,
                action=action,
                resource_type="http",
                resource_name=resource_name,
                detail=detail,
                tags=f"http,{action}",
            )
        except Exception as e:
            print("AuditMiddleware erro:", e)

        return response


class RequestMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        response = self.get_response(request)
        return response
    