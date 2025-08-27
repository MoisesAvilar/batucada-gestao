from django import forms
from .models import Transaction, Category, Aluno, CustomUser


class ProfessorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}".title()
        return obj.username.title()


class TransactionForm(forms.ModelForm):
    professor = ProfessorChoiceField(
        queryset=CustomUser.objects.filter(tipo__in=['professor', 'admin']).order_by('first_name', 'last_name'),
        required=False
    )

    class Meta:
        model = Transaction
        fields = ['description', 'amount', 'category', 'transaction_date', 'student', 'professor', 'observation']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['student'].queryset = Aluno.objects.order_by('nome_completo')

        self.fields['description'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Ex: Mensalidade, Conta de Luz'})
        self.fields['amount'].widget.attrs.update({'class': 'form-control', 'placeholder': '0.00'})
        self.fields['category'].widget.attrs.update({'class': 'form-select'})
        self.fields['transaction_date'].widget.attrs.update({'class': 'form-control', 'type': 'date'})
        self.fields['student'].widget.attrs.update({'class': 'form-select'})
        self.fields['professor'].widget.attrs.update({'class': 'form-select'})
        self.fields['observation'].widget.attrs.update({'class': 'form-control', 'rows': 3})

        self.fields['student'].label = "Aluno Relacionado"
        self.fields['professor'].label = "Professor Relacionado"


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['type'].widget.attrs.update({'class': 'form-select'})