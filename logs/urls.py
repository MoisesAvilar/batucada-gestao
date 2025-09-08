# logs/urls.py
from django.urls import path
from . import views

app_name = "logs"

urlpatterns = [
    # Página principal de logs
    path("", views.logs_page, name="logs_page"),
    # Endpoint da API que retorna logs em JSON
    path("api/", views.logs_api, name="logs_api"),
]
