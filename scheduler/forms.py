from django import forms
from django.forms import inlineformset_factory, modelformset_factory
from .models import (
    Aluno,
    Aula,
    Modalidade,
    CustomUser,
    RelatorioAula,
    ItemRudimento,
    ItemRitmo,
    ItemVirada,
    PresencaAluno,
    PresencaProfessor,
)


class TitlecaseModelChoiceField(forms.ModelChoiceField):
    """
    Um ModelChoiceField customizado que exibe as opções em letras maiúsculas.
    """

    def label_from_instance(self, obj):
        # Sobrescrevemos este método para formatar o texto de cada opção.
        # Ele pega a representação em string padrão do objeto (ex: aluno.nome_completo)
        # e a converte para maiúsculas.
        return str(obj).title()


class AulaForm(forms.ModelForm):
    """
    Formulário principal, contendo apenas os campos que não se repetem.
    A seleção de alunos/professores será feita pelos formsets.
    """

    recorrente_mensal = forms.BooleanField(
        required=False,
        label="Agendar recorrentemente (todas as semanas do mês)",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    modalidade = TitlecaseModelChoiceField(
        queryset=Modalidade.objects.all().order_by("nome"),
        label="Categoria",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Aula
        fields = ["modalidade", "data_hora", "status"]
        widgets = {
            "data_hora": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
            "modalidade": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


# --- Formulários Base para os Formsets ---
class AlunoChoiceForm(forms.Form):
    """
    Um formulário simples que contém apenas um campo <select> para um Aluno.
    Este será o "molde" para cada linha no nosso formset de alunos.
    """

    aluno = TitlecaseModelChoiceField(
        queryset=Aluno.objects.all().order_by("nome_completo"),
        label="Aluno",
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Selecione...",
    )


class ProfessorChoiceForm(forms.Form):
    """
    Um formulário simples que contém apenas um campo <select> para um Professor.
    Este será o "molde" para cada linha no nosso formset de professores.
    """

    professor = TitlecaseModelChoiceField(
        queryset=CustomUser.objects.filter(tipo__in=["professor", "admin"]).order_by(
            "username"
        ),
        label="Professor",
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Selecione...",
    )


class AlunoForm(forms.ModelForm):
    criar_recorrencia = forms.BooleanField(
        required=False,
        initial=True, # Já vem marcado por padrão
        label="Criar recorrência de mensalidade automaticamente",
        help_text="Se marcado, uma regra de receita recorrente será criada para este aluno."
    )
    class Meta:
        model = Aluno
        # Adicionamos os novos campos
        fields = [
            "status",
            "nome_completo",
            "email",
            "telefone",
            "cpf",
            "responsavel_nome",
            "data_criacao",
            "valor_mensalidade",
            "dia_vencimento",
        ]

        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "nome_completo": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "(XX) XXXXX-XXXX"}
            ),
            "cpf": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "000.000.000-00"}
            ),  # Widget para CPF
            "responsavel_nome": forms.TextInput(
                attrs={"class": "form-control"}
            ),  # Widget para Responsável
            "data_criacao": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"
            ),
            "valor_mensalidade": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Ex: 350.00"}
            ),
            "dia_vencimento": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Ex: 10"}
            ),
        }
        # 3. (Opcional) Adicionamos textos de ajuda para guiar o usuário
        help_texts = {
            "dia_vencimento": "Insira apenas o dia (um número de 1 a 31).",
        }
        labels = {
            "valor_mensalidade": "Valor da Mensalidade (R$)",
        }


class ModalidadeForm(forms.ModelForm):
    class Meta:
        model = Modalidade
        fields = ["nome", "valor_pagamento_professor", "tipo_pagamento"]
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nome da nova categoria",
                }
            ),
            "valor_pagamento_professor": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0.00"
                }
            ),
            "tipo_pagamento": forms.Select(
                attrs={
                    "class": "form-select"
                }
            )
        }


class ProfessorForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "tipo",
            "is_active",
            "is_staff",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
        label="Senha (apenas para criação)",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
        label="Confirmar Senha",
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if self.instance.pk is None:
            if not password:
                self.add_error(
                    "password", "Este campo é obrigatório para um novo usuário."
                )
            if password and password_confirm and password != password_confirm:
                self.add_error("password_confirm", "As senhas não coincidem.")
        elif password or password_confirm:
            if password and password_confirm and password != password_confirm:
                self.add_error("password_confirm", "As senhas não coincidem.")
            elif not password:
                self.add_error(
                    "password",
                    "A senha não pode ser vazia se a confirmação for preenchida.",
                )

        return cleaned_data

    def save(self, commit=True):
        # ... (sua lógica para salvar a senha)
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


# --- NOVOS FORMULÁRIOS PARA O RELATÓRIO DE AULA ---


class RelatorioAulaForm(forms.ModelForm):
    """
    Formulário principal para o Relatório, agora contendo apenas
    os campos que não são repetíveis.
    """

    class Meta:
        model = RelatorioAula
        fields = [
            "conteudo_teorico",
            "observacoes_teoria",
            "repertorio_musicas",
            "observacoes_repertorio",
            "observacoes_gerais",
        ]
        widgets = {
            "conteudo_teorico": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "observacoes_teoria": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Observações sobre o desenvolvimento teórico do aluno...",
                }
            ),
            "repertorio_musicas": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "observacoes_repertorio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Observações sobre a execução do repertório...",
                }
            ),
            "observacoes_gerais": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
        }


# --- FORMSETS PARA OS ITENS DINÂMICOS ---

ItemRudimentoFormSet = inlineformset_factory(
    parent_model=RelatorioAula,
    model=ItemRudimento,
    # ADICIONE O NOVO CAMPO AQUI
    fields=("descricao", "bpm", "duracao_min", "observacoes"),
    extra=1,
    can_delete=True,
    widgets={
        "descricao": forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Ex: Toque simples"}
        ),
        "bpm": forms.TextInput(attrs={"class": "form-control", "placeholder": "BPM"}),
        "duracao_min": forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Minutos"}
        ),
        # ADICIONE O WIDGET PARA O NOVO CAMPO
        "observacoes": forms.Textarea(
            attrs={
                "class": "form-control mt-2",
                "rows": 2,
                "placeholder": "Observações sobre este exercício...",
            }
        ),
    },
)

ItemRitmoFormSet = inlineformset_factory(
    parent_model=RelatorioAula,
    model=ItemRitmo,
    # ADICIONE O NOVO CAMPO AQUI
    fields=("descricao", "livro_metodo", "bpm", "duracao_min", "observacoes"),
    extra=1,
    can_delete=True,
    widgets={
        "descricao": forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Ex: Leitura da página 15"}
        ),
        "livro_metodo": forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Livro/Método"}
        ),
        "bpm": forms.TextInput(attrs={"class": "form-control", "placeholder": "BPM"}),
        "duracao_min": forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Minutos"}
        ),
        # ADICIONE O WIDGET PARA O NOVO CAMPO
        "observacoes": forms.Textarea(
            attrs={
                "class": "form-control mt-2",
                "rows": 2,
                "placeholder": "Observações sobre este exercício...",
            }
        ),
    },
)

ItemViradaFormSet = inlineformset_factory(
    parent_model=RelatorioAula,
    model=ItemVirada,
    # ADICIONE O NOVO CAMPO AQUI
    fields=("descricao", "bpm", "duracao_min", "observacoes"),
    extra=1,
    can_delete=True,
    widgets={
        "descricao": forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ex: Virada com 2 notas por tempo",
            }
        ),
        "bpm": forms.TextInput(attrs={"class": "form-control", "placeholder": "BPM"}),
        "duracao_min": forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Minutos"}
        ),
        # ADICIONE O WIDGET PARA O NOVO CAMPO
        "observacoes": forms.Textarea(
            attrs={
                "class": "form-control mt-2",
                "rows": 2,
                "placeholder": "Observações sobre este exercício...",
            }
        ),
    },
)


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "email",
            "username",
        ]  # Campos que o usuário pode editar
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Seu primeiro nome"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Seu sobrenome"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "seu@email.com"}
            ),
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Seu nome de usuário"}
            ),
        }

    # Validações adicionais, se necessário (ex: username único, email único)
    def clean_username(self):
        username = self.cleaned_data["username"]
        if (
            CustomUser.objects.filter(username=username)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("Este nome de usuário já está em uso.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email


class PresencaAlunoForm(forms.ModelForm):
    """Formulário para um único registro de presença de aluno."""

    class Meta:
        model = PresencaAluno
        fields = ["status"]
        widgets = {
            "status": forms.RadioSelect(attrs={"class": "form-check-input"}),
        }


# Usamos modelformset_factory para criar/editar múltiplos registros de presença de uma vez.
PresencaAlunoFormSet = modelformset_factory(
    PresencaAluno,
    form=PresencaAlunoForm,
    extra=0,  # Não mostra formulários em branco por padrão
    can_delete=False,
)


class PresencaProfessorForm(forms.ModelForm):
    """Formulário para um único registro de presença de professor."""

    class Meta:
        model = PresencaProfessor
        fields = ["status"]
        widgets = {
            "status": forms.RadioSelect(attrs={"class": "form-check-input"}),
        }


PresencaProfessorFormSet = modelformset_factory(
    PresencaProfessor, form=PresencaProfessorForm, extra=0, can_delete=False
)
