from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
from django.forms.models import model_to_dict
from django.utils import timezone
from .models import AuditLog


def safe_model_to_dict(instance):
    """
    Serializa instâncias de modelos Django para um dicionário JSON-safe.
    Converte ForeignKey em PK e ManyToMany em lista de PKs.
    """
    data = model_to_dict(instance)

    # Corrigir campos ManyToMany
    for field in instance._meta.many_to_many:
        data[field.name] = list(getattr(instance, field.name).values_list("id", flat=True))

    # Corrigir campos ForeignKey
    for field in instance._meta.fields:
        if field.many_to_one:  # ForeignKey
            related_obj = getattr(instance, field.name)
            data[field.name] = related_obj.pk if related_obj else None

    return data


def log_instance_action(instance, action, detail=None, user=None, request=None):
    resource_type = instance._meta.model_name.title()
    resource_id = str(instance.pk)
    resource_name = str(instance)

    # se não for passado, usa todos os campos
    if detail is None:
        detail = safe_model_to_dict(instance)

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
    elif user:
        username = user.get_full_name() if hasattr(user, "get_full_name") else str(user)

    AuditLog.objects.create(
        user=user if user else None,
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
        metadata={"timestamp": str(timezone.now())},
        tags=f"{resource_type.lower()},{action.lower()}",
    )


# --- Registrar signals para todos os modelos do sistema ---
ignored_apps = ["sessions", "admin", "auth", "contenttypes", "logs"]

# dicionário para guardar estados antes do save
_pre_save_snapshots = {}


for model in apps.get_models():
    app_label = model._meta.app_label
    if app_label in ignored_apps:
        continue

    @receiver(pre_save, sender=model)
    def pre_save_snapshot(sender, instance, **kwargs):
        """Salva o estado antigo antes de atualizar"""
        if not instance.pk:
            return
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            _pre_save_snapshots[(sender, instance.pk)] = safe_model_to_dict(old_instance)
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
                # só guarda campos alterados
                changes = {}
                for field, old_val in old_data.items():
                    new_val = new_data.get(field)
                    if old_val != new_val:
                        changes[field] = {"old": old_val, "new": new_val}

                if changes:
                    log_instance_action(instance, "Atualizou", detail=changes)

    @receiver(post_delete, sender=model)
    def post_delete_log(sender, instance, **kwargs):
        log_instance_action(instance, "Deletou")
