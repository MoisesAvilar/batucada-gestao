from django import forms
from .models import Aluno, Aula, Modalidade, RelatorioAula, CustomUser


class AulaForm(forms.ModelForm):
    recorrente_mensal = forms.BooleanField(
        required=False,
        label="Agendar recorrentemente (todas as semanas do mês)",
        help_text="Marque para agendar a aula no mesmo dia da semana e horário para todas as semanas do mês atual.",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Aula
        fields = ["aluno", "professor", "modalidade", "data_hora", "status"]

        widgets = {
            "data_hora": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"},
                format="%Y-%m-%dT%H:%M",
            ),
            "aluno": forms.Select(attrs={"class": "form-select"}),
            "professor": forms.Select(attrs={"class": "form-select"}),
            "modalidade": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }


class RelatorioAulaForm(forms.ModelForm):
    class Meta:
        model = RelatorioAula
        fields = [
            'conteudo_teorico',
            'exercicios_rudimentos',
            'bpm_rudimentos',
            'exercicios_ritmo',
            'livro_ritmo',
            'clique_ritmo',
            'exercicios_viradas',
            'clique_viradas',
            'repertorio_musicas',
            'observacoes_gerais'
        ]
        widgets = {
            'conteudo_teorico': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'exercicios_rudimentos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'bpm_rudimentos': forms.TextInput(attrs={'class': 'form-control'}),
            'exercicios_ritmo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'livro_ritmo': forms.TextInput(attrs={'class': 'form-control'}),
            'clique_ritmo': forms.TextInput(attrs={'class': 'form-control'}),
            'exercicios_viradas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'clique_viradas': forms.TextInput(attrs={'class': 'form-control'}),
            'repertorio_musicas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observacoes_gerais': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }


class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = ["nome_completo", "email", "telefone"]
        widgets = {
            "nome_completo": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "(XX) XXXXX-XXXX"}
            ),
        }


class ModalidadeForm(forms.ModelForm):
    class Meta:
        model = Modalidade
        fields = ["nome"]
        widgets = {
            "nome": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nome da nova modalidade",
                }
            )
        }


class ProfessorForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'tipo', 'is_active', 'is_staff']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False, label="Senha (apenas para criação)")
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False, label="Confirmar Senha")

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if self.instance.pk is None:
            if not password:
                self.add_error('password', "Este campo é obrigatório para um novo usuário.")
            if password and password_confirm and password != password_confirm:
                self.add_error('password_confirm', "As senhas não coincidem.")
        elif password or password_confirm:
            if password and password_confirm and password != password_confirm:
                self.add_error('password_confirm', "As senhas não coincidem.")
            elif not password:
                 self.add_error('password', "A senha não pode ser vazia se a confirmação for preenchida.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user
