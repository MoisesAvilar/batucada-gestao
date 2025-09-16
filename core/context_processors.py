from .models import UnidadeNegocio, Notificacao
from django.urls import reverse
from leads.forms import LeadForm
from finances.models import Despesa, Receita
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
            request.session.pop("unidade_ativa_id", None)

    return {"unidades_de_negocio": unidades, "unidade_ativa": unidade_ativa}


def add_lead_form_processor(request):
    if request.user.is_authenticated:
        return {'add_lead_form': LeadForm()}
    return {}


def notificacoes_vencimento(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'tipo') or request.user.tipo != 'admin':
        return {}

    unidade_ativa_id = request.session.get('unidade_ativa_id')
    if not unidade_ativa_id:
        return {}

    # --- DICIONÁRIO DE TRADUÇÃO ADICIONADO ---
    MESES_PT_ABREV = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
    }

    hoje = timezone.now().date()
    data_limite = hoje + timedelta(days=5)
    
    # LÓGICA PARA RECEITAS A VENCER
    receitas_a_vencer = Receita.objects.filter(
        unidade_negocio_id=unidade_ativa_id, status='a_receber',
        data_competencia__gte=hoje, data_competencia__lte=data_limite
    )
    for receita in receitas_a_vencer:
        # --- LÓGICA DO TÍTULO ALTERADA ---
        mes_abrev = MESES_PT_ABREV[receita.data_competencia.month]
        ano = receita.data_competencia.year
        titulo = f"Vencimento: {receita.descricao} ({mes_abrev}/{ano})"
        
        mensagem = f"Conta de R$ {receita.valor} vence em {receita.data_competencia.strftime('%d/%m')}."
        
        Notificacao.objects.get_or_create(
            usuario=request.user,
            titulo=titulo,
            tipo='receita',
            defaults={
                'mensagem': mensagem, 
                'url': reverse('finances:receita_list') + f'?descricao={receita.descricao}'
            }
        )

    # LÓGICA PARA DESPESAS A VENCER
    despesas_a_vencer = Despesa.objects.filter(
        unidade_negocio_id=unidade_ativa_id, status='a_pagar',
        data_competencia__gte=hoje, data_competencia__lte=data_limite
    )
    for despesa in despesas_a_vencer:
        # --- LÓGICA DO TÍTULO ALTERADA ---
        mes_abrev = MESES_PT_ABREV[despesa.data_competencia.month]
        ano = despesa.data_competencia.year
        titulo = f"Pagamento: {despesa.descricao} ({mes_abrev}/{ano})"

        mensagem = f"Conta de R$ {despesa.valor} vence em {despesa.data_competencia.strftime('%d/%m')}."
        
        Notificacao.objects.get_or_create(
            usuario=request.user,
            titulo=titulo,
            tipo='despesa',
            defaults={
                'mensagem': mensagem, 
                'url': reverse('finances:despesa_list') + f'?descricao={despesa.descricao}'
            }
        )

    # A busca das notificações não lidas para exibir
    notificacoes_nao_lidas = request.user.notificacoes.filter(lida=False)
    
    return {
        'notificacoes_dropdown': notificacoes_nao_lidas.order_by('-data_criacao')[:5], 
        'contagem_notificacoes_nao_lidas': notificacoes_nao_lidas.count(),
    }
