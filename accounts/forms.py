from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from scheduler.models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adicionamos atributos aos widgets dos campos existentes
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Escolha um nome de usuário",
                "required": True,
            }
        )
        self.fields["email"].widget.attrs.update(
            {"class": "form-control", "placeholder": "seu@email.com", "required": True}
        )
        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Crie uma senha forte",
                "required": True,
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Confirme sua senha",
                "required": True,
            }
        )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("username", "email")


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Usuário ou e-mail",
                "required": True,
            }
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Senha", "required": True}
        )
