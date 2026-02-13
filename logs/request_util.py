import threading

_thread_locals = threading.local()


def set_current_request(request):
    _thread_locals.request = request
    # Reseta snapshots a cada nova requisição para evitar vazamento de dados entre requests
    _thread_locals.snapshots = {}


def get_current_request():
    return getattr(_thread_locals, "request", None)


def set_model_snapshot(key, data):
    """Salva o estado anterior do objeto na thread atual."""
    if not hasattr(_thread_locals, "snapshots"):
        _thread_locals.snapshots = {}
    _thread_locals.snapshots[key] = data


def get_model_snapshot(key):
    """Recupera o estado anterior."""
    if not hasattr(_thread_locals, "snapshots"):
        return None
    return _thread_locals.snapshots.pop(key, None)
