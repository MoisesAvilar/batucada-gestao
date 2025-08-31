from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.urls import reverse


def set_unidade_negocio(request, pk):
    request.session["unidade_ativa_id"] = pk

    # Volta para a página anterior de onde o usuário veio
    referer_url = request.META.get("HTTP_REFERER", reverse("scheduler:dashboard"))
    return HttpResponseRedirect(referer_url)
