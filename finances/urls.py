from django.urls import path
from . import views


app_name = "finances"

urlpatterns = [
    path("", views.transaction_list_view, name="transaction_list"),
    path('ajax/add-category/', views.add_category_ajax, name='add_category_ajax'),
    path('delete/<int:pk>/', views.delete_transaction_view, name='delete_transaction'),
    path('edit/<int:pk>/', views.edit_transaction_view, name='edit_transaction'),
    path('contas-a-pagar/', views.despesa_list_view, name='despesa_list'),
    path('contas-a-pagar/baixar/<int:pk>/', views.baixar_despesa_view, name='baixar_despesa'),
    path('contas-a-receber/', views.receita_list_view, name='receita_list'),
    path('contas-a-receber/baixar/<int:pk>/', views.baixar_receita_view, name='baixar_receita'),
    path('contas-a-pagar/delete/<int:pk>/', views.delete_despesa_view, name='delete_despesa'),
    path('contas-a-pagar/edit/<int:pk>/', views.edit_despesa_view, name='edit_despesa'),
    path('contas-a-receber/delete/<int:pk>/', views.delete_receita_view, name='delete_receita'),
    path('contas-a-receber/edit/<int:pk>/', views.edit_receita_view, name='edit_receita'),
    path('recorrencias/', views.recorrencia_list_view, name='recorrencia_list'),
    path('recorrencias/despesa/delete/<int:pk>/', views.delete_despesa_recorrente_view, name='delete_despesa_recorrente'),
    path('recorrencias/despesa/edit/<int:pk>/', views.edit_despesa_recorrente_view, name='edit_despesa_recorrente'),
    path('recorrencias/receita/delete/<int:pk>/', views.delete_receita_recorrente_view, name='delete_receita_recorrente'),
    path('recorrencias/receita/edit/<int:pk>/', views.edit_receita_recorrente_view, name='edit_receita_recorrente'),
    path('dre/', views.dre_view, name='dre_report'),
]
