# Arquivo: leads/urls.py

from django.urls import path
from . import views

app_name = "leads"

urlpatterns = [
    path("", views.lead_listar, name="lead_listar"),
    path('<int:pk>/', views.lead_detalhe, name='lead_detalhe'),
    path('dashboard/', views.dashboard_leads, name='dashboard_leads'),
    path("novo/", views.lead_criar, name="lead_criar"),
    path("converter/<int:pk>/", views.converter_lead, name="converter_lead"),

    path('captura/', views.captura_lead_publica, name='captura_lead_publica'),
    path('sucesso/', views.captura_sucesso, name='captura_sucesso'),

    path('kanban/', views.kanban_board, name='kanban_board'),
    path('api/update-status/', views.update_lead_status, name='update_lead_status'),
    path('<int:pk>/edit/', views.lead_edit, name='lead_edit'),
    path('<int:pk>/delete/', views.lead_delete, name='lead_delete'),
]
