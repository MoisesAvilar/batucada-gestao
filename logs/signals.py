from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from .models import AuditLog
from .request_util import get_current_request, set_model_snapshot, get_model_snapshot

# Apps que NÃO devem gerar logs
IGNORED_APPS = [
    "sessions",
    "admin",
    "auth",
    "contenttypes",
    "logs",
    "simple_history",
    "auditlog",
]


def safe_model_to_dict(instance):
    """Serializa a instância de forma segura."""
    try:
        data = model_to_dict(instance)
        # Tenta enriquecer com representação de FKs e M2M
        if hasattr(instance, "_meta"):
            for field in instance._meta.many_to_many:
                if field.name in data:
                    related_manager = getattr(instance, field.name, None)
                    if related_manager:
                        data[field.name] = [str(obj) for obj in related_manager.all()]

            for field in instance._meta.fields:
                if field.many_to_one and field.name in data:
                    val = getattr(instance, field.name, None)
                    if val:
                        data[field.name] = str(val)
        return data
    except Exception:
        return {}


def log_instance_action(instance, action, detail=None):
    request = get_current_request()
    user = getattr(request, "user", None) if request else None

    resource_type = instance._meta.model_name.title()
    resource_id = str(instance.pk)
    resource_name = str(instance)

    username = "Sistema"
    ip = ""
    ua = ""
    path = ""
    method = ""

    if request:
        path = request.path
        method = request.method
        ip = request.META.get("REMOTE_ADDR") or request.META.get("HTTP_X_FORWARDED_FOR")
        ua = request.META.get("HTTP_USER_AGENT", "")[:1000]
        if user and user.is_authenticated:
            username = user.get_full_name() or user.username
    elif user:
        username = str(user)

    try:
        AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            username=username,
            ip_address=ip,
            user_agent=ua,
            path=path,
            method=method,
            action=action.lower(),
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            detail=detail,
            tags=f"{resource_type.lower()},{action.lower()}",
        )
    except Exception as e:
        print(f"Erro ao salvar log: {e}")


# --- RECEPTORES GLOBAIS ---


@receiver(pre_save)
def global_pre_save(sender, instance, **kwargs):
    if sender._meta.app_label in IGNORED_APPS:
        return

    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            old_data = safe_model_to_dict(old_instance)
            set_model_snapshot((sender, instance.pk), old_data)
        except sender.DoesNotExist:
            pass
        except Exception:
            pass


@receiver(post_save)
def global_post_save(sender, instance, created, **kwargs):
    if sender._meta.app_label in IGNORED_APPS:
        return

    try:
        if created:
            log_instance_action(instance, "Criou", detail=safe_model_to_dict(instance))
        else:
            old_data = get_model_snapshot((sender, instance.pk))
            new_data = safe_model_to_dict(instance)

            changes = {}
            if old_data:
                for field, old_val in old_data.items():
                    new_val = new_data.get(field)
                    if str(old_val) != str(new_val):
                        changes[field] = {"old": old_val, "new": new_val}

            if changes:
                log_instance_action(instance, "Atualizou", detail=changes)
            elif not old_data:
                log_instance_action(instance, "Atualizou (Sem Diff)", detail=new_data)

    except Exception as e:
        print(f"Erro no post_save log: {e}")


@receiver(post_delete)
def global_post_delete(sender, instance, **kwargs):
    if sender._meta.app_label in IGNORED_APPS:
        return

    try:
        detail = safe_model_to_dict(instance)
        log_instance_action(instance, "Deletou", detail=detail)
    except Exception:
        pass
