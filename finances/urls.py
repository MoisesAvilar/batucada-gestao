from django.urls import path
from . import views


app_name = "finances"

urlpatterns = [
    path("", views.transaction_list_view, name="transaction_list"),
    path('ajax/add-category/', views.add_category_ajax, name='add_category_ajax'),
    path('ajax/get-aluno-details/<int:aluno_id>/', views.get_aluno_details, name='ajax_get_aluno_details'),
    path('ajax/calcular-pagamento-professor/', views.calcular_pagamento_professor_ajax, name='ajax_calcular_pagamento_professor'),
    path('receitas/add/mensalidade/', views.add_mensalidade, name='add_mensalidade'),
    path('receitas/add/venda/', views.add_venda, name='add_venda'),
    path('contas-a-pagar/', views.despesa_list_view, name='despesa_list'),
    path('contas-a-pagar/baixar/<int:pk>/', views.baixar_despesa_view, name='baixar_despesa'),
    path('contas-a-receber/', views.receita_list_view, name='receita_list'),
    path('contas-a-receber/baixar/<int:pk>/', views.baixar_receita_view, name='baixar_receita'),
    path('contas-a-pagar/delete/<int:pk>/', views.delete_despesa_view, name='delete_despesa'),
    path('contas-a-pagar/edit/<int:pk>/', views.edit_despesa_view, name='edit_despesa'),
    path('contas-a-receber/delete/<int:pk>/', views.delete_receita_view, name='delete_receita'),
    path('receitas/mensalidade/<int:pk>/edit/', views.edit_mensalidade, name='edit_mensalidade'),
    path('receitas/venda/<int:pk>/edit/', views.edit_venda, name='edit_venda'),
    path('recorrencias/', views.recorrencia_list_view, name='recorrencia_list'),
    path('recorrencias/toggle-ativa/', views.toggle_recorrencia_ativa, name='toggle_recorrencia_ativa'),
    path('recorrencias/despesa/delete/<int:pk>/', views.delete_despesa_recorrente_view, name='delete_despesa_recorrente'),
    path('recorrencias/despesa/edit/<int:pk>/', views.edit_despesa_recorrente_view, name='edit_despesa_recorrente'),
    path('recorrencias/receita/delete/<int:pk>/', views.delete_receita_recorrente_view, name='delete_receita_recorrente'),
    path('recorrencias/receita/edit/<int:pk>/', views.edit_receita_recorrente_view, name='edit_receita_recorrente'),
    path('dre/detalhes/', views.dre_details_view, name='dre_details'),
    path('dre/', views.dre_view, name='dre_report'),
    path('dre/export/xlsx/', views.export_dre_xlsx, name='export_dre_xlsx'),
    path('dre/export/pdf/', views.export_dre_pdf, name='export_dre_pdf'),
    path('aging-report/', views.aging_report_view, name='aging_report'),
]
