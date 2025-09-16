from django import forms
from .models import (
    Transaction,
    Category,
    Aluno,
    CustomUser,
    Despesa,
    Receita,
    DespesaRecorrente,
    ReceitaRecorrente,
)
from store.models import Produto

# ==============================================================================
# NOVOS FORMULÁRIOS DE RECEITA (INÍCIO DA NOSSA ALTERAÇÃO)
# ==============================================================================


class CategoryChoiceField(forms.ModelChoiceField):
    """
    Um campo de formulário que exibe o nome da categoria com a primeira letra maiúscula.
    """
    def label_from_instance(self, obj):
        return obj.name.title()


class MensalidadeReceitaForm(forms.ModelForm):
    """
    Formulário especializado APENAS para o lançamento de mensalidades.
    """

    class Meta:
        model = Receita
        fields = [
            "aluno",
            "descricao",
            "valor",
            "categoria",
            "data_competencia",
            "data_recebimento",
        ]
        widgets = {
            "data_competencia": forms.DateInput(attrs={"type": "date"}),
            "data_recebimento": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtros e Otimizações
        self.fields["categoria"] = CategoryChoiceField(
            queryset=Category.objects.filter(type="income"),
            widget=forms.Select(attrs={"class": "form-select"})
        )
        self.fields["aluno"].queryset = Aluno.objects.filter(status="ativo").order_by(
            "nome_completo"
        )

        # O campo aluno é obrigatório para mensalidades
        self.fields["aluno"].required = True
        self.fields["data_recebimento"].required = False  # Recebimento pode ser futuro

        # Adiciona classes do Bootstrap
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({"class": "form-select"})
            else:
                field.widget.attrs.update({"class": "form-control"})


class VendaReceitaForm(forms.ModelForm):
    """
    Formulário especializado APENAS para o registro de vendas de produtos.
    """

    class Meta:
        model = Receita
        fields = [
            "produto",
            "quantidade",
            "descricao",
            "valor",
            "categoria",
            "aluno",
            "data_competencia",
            "data_recebimento",
        ]
        widgets = {
            "data_competencia": forms.DateInput(attrs={"type": "date"}),
            "data_recebimento": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {"aluno": "Associar Venda ao Aluno (Opcional)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtros e Otimizações
        self.fields["categoria"] = CategoryChoiceField(
            queryset=Category.objects.filter(type="income"),
            widget=forms.Select(attrs={"class": "form-select"})
        )
        self.fields["produto"].queryset = Produto.objects.filter(
            quantidade_em_estoque__gt=0
        ).order_by("nome")
        self.fields["aluno"].queryset = Aluno.objects.filter(status="ativo").order_by(
            "nome_completo"
        )

        # O campo aluno é opcional para vendas
        self.fields["aluno"].required = False
        self.fields["data_recebimento"].required = False  # Recebimento pode ser futuro

        # Adiciona classes do Bootstrap
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({"class": "form-select"})
            else:
                field.widget.attrs.update({"class": "form-control"})


# ==============================================================================
# FIM DA NOSSA ALTERAÇÃO (O RESTANTE DO ARQUIVO PERMANECE COMO ESTAVA)
# ==============================================================================


class ProfessorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}".title()
        return obj.username.title()


class TransactionForm(forms.ModelForm):
    professor = ProfessorChoiceField(
        queryset=CustomUser.objects.filter(tipo__in=["professor", "admin"]).order_by(
            "first_name", "last_name"
        ),
        required=False,
    )

    class Meta:
        model = Transaction
        fields = [
            "description",
            "amount",
            "category",
            "transaction_date",
            "student",
            "professor",
            "observation",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["student"].queryset = Aluno.objects.order_by("nome_completo")

        self.fields["description"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Ex: Mensalidade, Conta de Luz"}
        )
        self.fields["amount"].widget.attrs.update(
            {"class": "form-control", "placeholder": "0.00"}
        )
        self.fields["category"].widget.attrs.update({"class": "form-select"})
        self.fields["transaction_date"].widget.attrs.update(
            {"class": "form-control", "type": "date"}
        )
        self.fields["student"].widget.attrs.update({"class": "form-select"})
        self.fields["professor"].widget.attrs.update({"class": "form-select"})
        self.fields["observation"].widget.attrs.update(
            {"class": "form-control", "rows": 3}
        )

        self.fields["student"].label = "Aluno Relacionado"
        self.fields["professor"].label = "Professor Relacionado"


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "type", "tipo_dre"]
        widgets = {
            'tipo_dre': forms.RadioSelect(attrs={'class': 'btn-check'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs.update({"class": "form-control"})
        self.fields["type"].widget = forms.HiddenInput()
        self.fields["tipo_dre"].label = "Classificar como:"
        self.fields["tipo_dre"].empty_label = None


class DespesaForm(forms.ModelForm):
    professor = ProfessorChoiceField(
        queryset=CustomUser.objects.filter(tipo__in=["professor", "admin"]).order_by(
            "first_name", "last_name"
        ),
        required=False,
    )

    class Meta:
        model = Despesa
        fields = [
            "descricao",
            "valor",
            "categoria",
            "data_competencia",
            "data_pagamento",
            "professor",
        ]
        widgets = {
            "data_competencia": forms.DateInput(attrs={"type": "date"}),
            "data_pagamento": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"] = CategoryChoiceField(
            queryset=Category.objects.filter(type="expense"),
            widget=forms.Select(attrs={"class": "form-control"}) # Mantém form-control aqui
        )

        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"


# O ANTIGO ReceitaForm FOI REMOVIDO DAQUI


class DespesaRecorrenteForm(forms.ModelForm):
    professor = ProfessorChoiceField(
        queryset=CustomUser.objects.filter(tipo__in=["professor", "admin"]).order_by(
            "first_name", "last_name"
        ),
        required=False,
    )

    class Meta:
        model = DespesaRecorrente
        fields = [
            "descricao",
            "valor",
            "categoria",
            "dia_do_mes",
            "data_inicio",
            "data_fim",
            "professor",
            "ativa",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "data_fim": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Category.objects.filter(type="expense")
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ != "CheckboxInput":
                field.widget.attrs.update({"class": "form-control"})


class ReceitaRecorrenteForm(forms.ModelForm):
    class Meta:
        model = ReceitaRecorrente
        fields = [
            "descricao",
            "valor",
            "categoria",
            "dia_do_mes",
            "data_inicio",
            "data_fim",
            "aluno",
            "ativa",
        ]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "data_fim": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Category.objects.filter(type="income")
        self.fields["aluno"].queryset = Aluno.objects.order_by("nome_completo")
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ != "CheckboxInput":
                field.widget.attrs.update({"class": "form-control"})

    def clean(self):
        cleaned_data = super().clean()
        aluno = cleaned_data.get("aluno")
        valor = cleaned_data.get("valor")

        if not aluno and not valor:
            raise forms.ValidationError(
                "Se nenhum aluno for selecionado, o campo 'Valor' é obrigatório."
            )

        if aluno:
            cleaned_data["valor"] = None
            cleaned_data["dia_do_mes"] = None

        return cleaned_data
