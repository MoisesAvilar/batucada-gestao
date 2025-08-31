from .models import UnidadeNegocio


def unidades_negocio_processor(request):
    unidades = UnidadeNegocio.objects.all()
    unidade_ativa_id = request.session.get("unidade_ativa_id")
    unidade_ativa = None

    if unidade_ativa_id:
        try:
            unidade_ativa = UnidadeNegocio.objects.get(pk=unidade_ativa_id)
        except UnidadeNegocio.DoesNotExist:
            # Limpa a sessão se o ID for inválido
            request.session.pop("unidade_ativa_id", None)

    return {"unidades_de_negocio": unidades, "unidade_ativa": unidade_ativa}
