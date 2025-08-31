from django import forms
from .models import Transaction, Category, Aluno, CustomUser, Despesa, Receita, DespesaRecorrente, ReceitaRecorrente


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


class DespesaForm(forms.ModelForm):
    # Reutilizamos o campo customizado para exibir os nomes corretamente
    professor = ProfessorChoiceField(
        queryset=CustomUser.objects.filter(tipo__in=['professor', 'admin']).order_by('first_name', 'last_name'),
        required=False
    )
    
    class Meta:
        model = Despesa
        fields = ['descricao', 'valor', 'categoria', 'data_competencia', 'data_pagamento', 'professor']
        widgets = {
            'data_competencia': forms.DateInput(attrs={'type': 'date'}),
            'data_pagamento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Category.objects.filter(type='expense')
        
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class ReceitaForm(forms.ModelForm):
    class Meta:
        model = Receita
        fields = ['descricao', 'valor', 'categoria', 'data_competencia', 'data_recebimento', 'aluno']
        widgets = {
            'data_competencia': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_recebimento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra para mostrar apenas categorias de 'income' e alunos ordenados
        self.fields['categoria'].queryset = Category.objects.filter(type='income')
        self.fields['aluno'].queryset = Aluno.objects.order_by('nome_completo')
        self.fields['aluno'].required = False # Aluno é opcional

        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class DespesaRecorrenteForm(forms.ModelForm):
    professor = ProfessorChoiceField(
        queryset=CustomUser.objects.filter(tipo__in=['professor', 'admin']).order_by('first_name', 'last_name'),
        required=False
    )

    class Meta:
        model = DespesaRecorrente
        fields = ['descricao', 'valor', 'categoria', 'dia_do_mes', 'data_inicio', 'data_fim', 'professor', 'ativa']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'data_fim': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Category.objects.filter(type='expense')
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ != 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-control'})


class ReceitaRecorrenteForm(forms.ModelForm):
    class Meta:
        model = ReceitaRecorrente
        fields = ['descricao', 'valor', 'categoria', 'dia_do_mes', 'data_inicio', 'data_fim', 'aluno', 'ativa']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'data_fim': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Category.objects.filter(type='income')
        self.fields['aluno'].queryset = Aluno.objects.order_by('nome_completo')
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ != 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        aluno = cleaned_data.get('aluno')
        valor = cleaned_data.get('valor')

        # Se não selecionou um aluno, então o valor é obrigatório
        if not aluno and not valor:
            raise forms.ValidationError("Se nenhum aluno for selecionado, o campo 'Valor' é obrigatório.")

        # Se selecionou um aluno, o valor e o dia não devem ser preenchidos (serão ignorados)
        if aluno:
            cleaned_data['valor'] = None
            cleaned_data['dia_do_mes'] = None
            
        return cleaned_data
