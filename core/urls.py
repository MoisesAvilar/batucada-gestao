from django.urls import path
from . import views


app_name = "core"

urlpatterns = [
    path("set-unidade/<int:pk>/", views.set_unidade_negocio, name="set_unidade_negocio",),
    path('notificacoes/marcar-como-lida/', views.marcar_notificacoes_como_lidas, name='marcar_notificacoes_lidas'),
    path('notificacoes/', views.notificacao_list_view, name='notificacao_list'),
    path('notificacoes/<int:pk>/marcar-nao-lida/', views.marcar_notificacao_nao_lida, name='marcar_notificacao_nao_lida'),
    path('notificacoes/<int:pk>/excluir/', views.excluir_notificacao, name='excluir_notificacao'),
]
