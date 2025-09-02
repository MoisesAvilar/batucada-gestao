from django import forms
from .models import Produto, CategoriaProduto


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = [
            "nome", "descricao", "categoria", "sku",
            "quantidade_em_estoque", "custo_de_aquisicao",
            "percentual_markup", "preco_de_venda_manual",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "form-control"})

    # --- INÍCIO DA LÓGICA DE VALIDAÇÃO CUSTOMIZADA ---
    def clean(self):
        cleaned_data = super().clean()
        custo = cleaned_data.get("custo_de_aquisicao")
        preco_manual = cleaned_data.get("preco_de_venda_manual")
        markup = cleaned_data.get("percentual_markup")

        # Validação 1: Markup não pode ser negativo
        if markup is not None and markup < 0:
            self.add_error('percentual_markup', "O markup não pode ser um valor negativo.")

        # Validação 2: Se um preço manual for definido, ele deve ser maior ou igual ao custo
        if preco_manual is not None and custo is not None:
            if preco_manual < custo:
                self.add_error('preco_de_venda_manual', "O preço de venda manual não pode ser menor que o custo de aquisição.")
        
        return cleaned_data


class CategoriaProdutoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProduto
        fields = ["nome"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome"].widget.attrs.update({"class": "form-control"})
