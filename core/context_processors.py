from .models import UnidadeNegocio
from leads.forms import LeadForm
from scheduler.models import Aluno
from finances.models import Despesa
from django.utils import timezone
from datetime import timedelta


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


def notificacoes_vencimento(request):
    """
    Verifica se há alunos com mensalidades a vencer E despesas a pagar nos próximos dias.
    """
    if not request.user.is_authenticated or not hasattr(request.user, 'tipo') or request.user.tipo != 'admin':
        return {}

    unidade_ativa_id = request.session.get('unidade_ativa_id')
    if not unidade_ativa_id:
        return {}

    hoje = timezone.now().date()
    
    # --- LÓGICA PARA RECEITAS (Contas a Receber) ---
    alunos_mensalistas = Aluno.objects.filter(
        status='ativo',
        valor_mensalidade__isnull=False,
        dia_vencimento__isnull=False
    )
    alunos_a_vencer = []
    for aluno in alunos_mensalistas:
        status_pagamento = aluno.get_status_pagamento()
        if status_pagamento['status'] == 'Próximo Venc.':
            alunos_a_vencer.append(aluno)

    # =======================================================
    # NOVA LÓGICA PARA DESPESAS (Contas a Pagar)
    # =======================================================
    dias_a_frente = 5
    data_limite = hoje + timedelta(days=dias_a_frente)

    despesas_a_vencer = Despesa.objects.filter(
        unidade_negocio_id=unidade_ativa_id,
        status='a_pagar',
        data_competencia__gte=hoje,
        data_competencia__lte=data_limite
    ).order_by('data_competencia')
    # =======================================================

    # Soma as contagens para o total
    contagem_total = len(alunos_a_vencer) + len(despesas_a_vencer)

    # Retorna todos os dados para o template
    return {
        'alunos_com_vencimento_proximo': alunos_a_vencer,
        'despesas_com_vencimento_proximo': despesas_a_vencer,
        'contagem_vencimentos_total': contagem_total,
    }
