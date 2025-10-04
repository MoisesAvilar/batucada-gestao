# logs/signals.py

from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
from django.forms.models import model_to_dict
from .models import AuditLog
from .request_util import get_current_request


def safe_model_to_dict(instance):
    """
    Serializa instâncias de modelos para um dicionário, enriquecendo
    os relacionamentos com uma representação em texto (repr).
    """
    data = model_to_dict(instance)

    for field in instance._meta.many_to_many:
        related_manager = getattr(instance, field.name)
        data[field.name] = [
            {'id': obj.pk, 'repr': str(obj)}
            for obj in related_manager.all()
        ]

    for field in instance._meta.fields:
        if field.many_to_one:  # ForeignKey
            related_obj = getattr(instance, field.name)
            if related_obj:
                data[field.name] = {
                    'id': related_obj.pk,
                    'repr': str(related_obj)
                }
            else:
                data[field.name] = None
    return data


def log_instance_action(instance, action, detail=None):
    # Agora pegamos o request e o usuário a partir dele
    request = get_current_request()
    user = getattr(request, "user", None) if request else None

    # Se a ação não tiver detalhes significativos, não registramos o log.
    if action.lower() == "atualizou" and not detail:
        return

    resource_type = instance._meta.model_name.title()
    resource_id = str(instance.pk)
    resource_name = str(instance)

    if detail is None:
        detail = safe_model_to_dict(instance)

    username = "system"
    ip = ""
    ua = ""
    path = ""
    method = ""

    if request and user and user.is_authenticated:
        username = user.get_full_name() or user.username
        ip = request.META.get("REMOTE_ADDR") or request.META.get("HTTP_X_FORWARDED_FOR")
        ua = request.META.get("HTTP_USER_AGENT", "")[:1000]
        path = request.path
        method = request.method
    elif user and user.is_authenticated:
        username = user.get_full_name() if hasattr(user, "get_full_name") else str(user)

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


# --- Registrar signals ---
ignored_apps = ["sessions", "admin", "auth", "contenttypes", "logs"]
_pre_save_snapshots = {}

for model in apps.get_models():
    app_label = model._meta.app_label
    if app_label in ignored_apps:
        continue

    @receiver(pre_save, sender=model)
    def pre_save_snapshot(sender, instance, **kwargs):
        if instance.pk:
            try:
                old_instance = sender.objects.get(pk=instance.pk)
                _pre_save_snapshots[(sender, instance.pk)] = safe_model_to_dict(
                    old_instance
                )
            except sender.DoesNotExist:
                pass

    @receiver(post_save, sender=model)
    def post_save_log(sender, instance, created, **kwargs):
        if created:
            log_instance_action(instance, "Criou")
        else:
            old_data = _pre_save_snapshots.pop((sender, instance.pk), None)
            new_data = safe_model_to_dict(instance)
            if old_data:
                changes = {}
                for field, old_val in old_data.items():
                    new_val = new_data.get(field)
                    if old_val != new_val:
                        changes[field] = {"old": old_val, "new": new_val}

                # Só cria o log se de fato houveram mudanças
                if changes:
                    log_instance_action(instance, "Atualizou", detail=changes)

    @receiver(post_delete, sender=model)
    def post_delete_log(sender, instance, **kwargs):
        log_instance_action(instance, "Deletou")
