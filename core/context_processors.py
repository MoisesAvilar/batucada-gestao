from .models import UnidadeNegocio
from leads.forms import LeadForm


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


def add_lead_form_processor(request):
    """
    Disponibiliza o formulário de adição de lead em todas as páginas.
    """
    # Só adiciona o formulário se o usuário estiver logado
    if request.user.is_authenticated:
        return {'add_lead_form': LeadForm()}
    return {}
