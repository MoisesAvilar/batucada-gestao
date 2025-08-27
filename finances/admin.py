from django.contrib import admin
from .models import Category, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "type")
    list_filter = ("type",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'category', 'transaction_date', 'student', 'professor')
    list_filter = ('category__type', 'category', 'transaction_date')
    search_fields = ('description', 'student__nome_completo', 'professor__username', 'observation')
    autocomplete_fields = ('category', 'student', 'professor', 'created_by')
    ordering = ('-transaction_date',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
