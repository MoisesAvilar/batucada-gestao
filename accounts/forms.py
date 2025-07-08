from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from scheduler.models import CustomUser
from django import forms
from django.core.validators import RegexValidator


class CustomUserCreationForm(UserCreationForm):
    password_validator = RegexValidator(
        regex=r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
        message="A senha deve ter no mínimo 8 caracteres, incluindo pelo menos uma letra maiúscula, uma minúscula, um número e um caractere especial."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget = forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Escolha um nome de usuário",
            "required": True,
        })
        self.fields["email"].widget = forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "seu@email.com",
            "required": True
        })
        self.fields["password1"].widget = forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Crie uma senha forte",
            "required": True,
        })
        self.fields['password1'].validators.append(self.password_validator)

        self.fields["password2"].widget = forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirme sua senha",
            "required": True,
        })
        
        self.fields['first_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Primeiro Nome'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Sobrenome'})
        
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True

        # REMOVIDO: Não precisamos mais do campo 'tipo' no __init__ para configuração de widget
        # self.fields['tipo'].widget.attrs.update({'class': 'form-select'})


    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # REMOVIDO: 'tipo' da lista de fields
        fields = ("username", "email", "first_name", "last_name") 
        error_messages = {
            'username': {
                'unique': "Este nome de usuário já está em uso. Por favor, escolha outro.",
            },
            'email': {
                'unique': "Este e-mail já está cadastrado. Por favor, use outro ou faça login.",
            },
        }

    # NOVO: Sobrescrever o método save para definir o tipo de usuário como 'professor'
    def save(self, commit=True):
        user = super().save(commit=False) # Salva o usuário sem comitar no banco ainda
        user.tipo = 'professor' # Define o tipo como 'professor'
        if commit:
            user.save() # Comita o usuário no banco
        return user


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget = forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Usuário ou e-mail",
            "required": True,
        })
        self.fields["password"].widget = forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Senha",
            "required": True,
        })