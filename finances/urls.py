from django.urls import path
from . import views


app_name = "finances"

urlpatterns = [
    path("", views.transaction_list_view, name="transaction_list"),
    path('ajax/add-category/', views.add_category_ajax, name='add_category_ajax'),
    path('delete/<int:pk>/', views.delete_transaction_view, name='delete_transaction'),
    path('edit/<int:pk>/', views.edit_transaction_view, name='edit_transaction'),
]
