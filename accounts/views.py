from django.shortcuts import redirect, render
from django.contrib.auth import login, logout
from django.contrib import messages
from .forms import (
    CustomAuthenticationForm,
    CustomUserCreationForm,
)


def sign_up_view(request):
    if request.method == "POST":
        user_form = CustomUserCreationForm(request.POST)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Sua conta foi criada com sucesso! Faça login para continuar.")
            return redirect("accounts:login")
    else:
        user_form = CustomUserCreationForm()
    return render(request, "accounts/sign_up.html", {"user_form": user_form})


def login_view(request):
    if request.method == "POST":
        login_form = CustomAuthenticationForm(
            request, data=request.POST
        )
        if login_form.is_valid():
            user = login_form.get_user()
            login(request, user)
            return redirect("scheduler:dashboard")
    else:
        login_form = CustomAuthenticationForm()

    return render(request, "accounts/login.html", {"login_form": login_form})


def logout_view(request):
    logout(request)
    return redirect("accounts:login")
