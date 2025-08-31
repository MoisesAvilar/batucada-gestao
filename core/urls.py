from django.urls import path
from . import views


app_name = "core"

urlpatterns = [
    path(
        "set-unidade/<int:pk>/", views.set_unidade_negocio, name="set_unidade_negocio"
    ),
]
