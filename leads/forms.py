import re
from django import forms
from .models import Lead, InteracaoLead
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class LeadForm(forms.ModelForm):
    data_criacao = forms.DateField(
        label="Data de Criação",
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date'}
        ),
        required=False
    )

    class Meta:
        model = Lead
        fields = [
            "nome_interessado",
            "nome_responsavel",
            "contato",
            "idade",
            "status",
            "data_criacao",
            "curso_interesse",
            "nivel_experiencia",
            "melhor_horario_contato",
            "fonte",
            "observacoes",
            # "proposito_estudo",
            # "objetivo_tocar",
            # "motivo_interesse_especifico",
            # "sobre_voce",
        ]
        widgets = {
            "nome_interessado": forms.TextInput(attrs={"class": "form-control"}),
            "nome_responsavel": forms.TextInput(attrs={"class": "form-control"}),
            "contato": forms.TextInput(
                attrs={
                    "class": "form-control contact-mask",
                    "placeholder": "(XX) XXXXX-XXXX ou email@exemplo.com",
                }
            ),
            "idade": forms.NumberInput(attrs={"class": "form-control"}),
            "fonte": forms.TextInput(attrs={"class": "form-control"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "curso_interesse": forms.Select(attrs={"class": "form-select"}),
            "nivel_experiencia": forms.Select(attrs={"class": "form-select"}),
            "melhor_horario_contato": forms.Select(attrs={"class": "form-select"}),
            # "proposito_estudo": forms.Textarea(
            #     attrs={"class": "form-control", "rows": 3}
            # ),
            # "objetivo_tocar": forms.Textarea(
            #     attrs={"class": "form-control", "rows": 3}
            # ),
            # "motivo_interesse_especifico": forms.Textarea(
            #     attrs={"class": "form-control", "rows": 3}
            # ),
            # "sobre_voce": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.data_criacao:
            self.initial['data_criacao'] = self.instance.data_criacao.strftime('%Y-%m-%d')

        self.fields['idade'].required = True
        self.fields['curso_interesse'].required = True
        self.fields['fonte'].required = True

        self.fields['fonte'].label = "Origem"

    def clean_contato(self):
        contato = self.cleaned_data.get("contato", "").strip()
        if "@" in contato:
            try:
                validate_email(contato)
                return contato
            except ValidationError:
                raise ValidationError(
                    "Por favor, insira um endereço de e-mail válido.",
                    code="invalid_email",
                )
        else:
            digits_only = re.sub(r"\D", "", contato)
            if len(digits_only) not in [10, 11]:
                raise ValidationError(
                    "O número de telefone deve ter 10 ou 11 dígitos (com DDD).",
                    code="invalid_phone",
                )
            return digits_only


class InteracaoLeadForm(forms.ModelForm):
    class Meta:
        model = InteracaoLead
        fields = ["tipo", "notas"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "notas": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Descreva o que foi conversado...",
                }
            ),
        }


class PublicLeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = [
            "nome_interessado",
            "nome_responsavel",
            "contato",
            "idade",
            "curso_interesse",
            "nivel_experiencia",
            "melhor_horario_contato",
            "proposito_estudo",
            "objetivo_tocar",
            "motivo_interesse_especifico",
            "sobre_voce",
            "fonte",
        ]
        widgets = {
            "nome_interessado": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Seu nome completo"}
            ),
            "nome_responsavel": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nome do responsável (se aplicável)",
                }
            ),
            "contato": forms.TextInput(
                attrs={
                    "class": "form-control contact-mask",
                    "placeholder": "(XX) XXXXX-XXXX ou seu e-mail",
                }
            ),
            "idade": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Idade do interessado"}
            ),
            "fonte": forms.HiddenInput(),
            "curso_interesse": forms.Select(attrs={"class": "form-select"}),
            "nivel_experiencia": forms.Select(attrs={"class": "form-select"}),
            "melhor_horario_contato": forms.Select(attrs={"class": "form-select"}),
            "proposito_estudo": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Ex: Tocar como hobby, me tornar profissional, etc.",
                }
            ),
            "objetivo_tocar": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Ex: Na igreja, em uma banda, em casa para a família...",
                }
            ),
            "motivo_interesse_especifico": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Ex: Sempre gostei do som, um amigo me indicou, etc.",
                }
            ),
            "sobre_voce": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Fale um pouco sobre suas experiências e expectativas.",
                }
            ),
        }

    def clean_contato(self):
        contato = self.cleaned_data.get("contato", "").strip()
        if "@" in contato:
            try:
                validate_email(contato)
                return contato
            except ValidationError:
                raise ValidationError(
                    "Por favor, insira um endereço de e-mail válido.",
                    code="invalid_email",
                )
        else:
            digits_only = re.sub(r"\D", "", contato)
            if len(digits_only) not in [10, 11]:
                raise ValidationError(
                    "O número de telefone deve ter 10 ou 11 dígitos (com DDD).",
                    code="invalid_phone",
                )
            return digits_only
