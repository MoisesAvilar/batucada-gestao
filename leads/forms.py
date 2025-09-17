from django import forms
from .models import Lead, InteracaoLead


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = [
            "nome_interessado",
            "nome_responsavel",
            "contato",
            "idade",
            "status",
            "curso_interesse",
            "nivel_experiencia",
            "melhor_horario_contato",
            "fonte",
            "observacoes",
            "proposito_estudo",
            "objetivo_tocar",
            "motivo_interesse_especifico",
            "sobre_voce",
        ]
        widgets = {
            "nome_interessado": forms.TextInput(attrs={"class": "form-control"}),
            "nome_responsavel": forms.TextInput(attrs={"class": "form-control"}),
            "contato": forms.TextInput(attrs={"class": "form-control"}),
            "idade": forms.NumberInput(attrs={"class": "form-control"}),
            "fonte": forms.TextInput(attrs={"class": "form-control"}),
            "observacoes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "curso_interesse": forms.Select(attrs={"class": "form-select"}),
            "nivel_experiencia": forms.Select(attrs={"class": "form-select"}),
            "melhor_horario_contato": forms.Select(attrs={"class": "form-select"}),
            "proposito_estudo": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "objetivo_tocar": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "motivo_interesse_especifico": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "sobre_voce": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


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
                    "class": "form-control",
                    "placeholder": "Seu melhor Telefone ou E-mail",
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
