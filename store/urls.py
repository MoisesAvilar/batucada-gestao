from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('produtos/', views.produto_list_view, name='produto_list'),

    # --- URLS ATUALIZADAS ---
    path('produtos/<int:pk>/editar/', views.produto_edit_view, name='produto_edit'),
    path('produtos/<int:pk>/excluir/', views.produto_delete_view, name='produto_delete'),

    path('ajax/add-categoria/', views.add_categoria_produto_ajax, name='add_categoria_ajax'),
]
