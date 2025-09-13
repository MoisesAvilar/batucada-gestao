from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Lead
from django.core.paginator import Paginator
from .forms import LeadForm, InteracaoLeadForm, PublicLeadForm
from urllib.parse import urlencode
from django.db.models import Count
import json


@login_required
def dashboard_leads(request):
    total_leads = Lead.objects.count()
    leads_convertidos = Lead.objects.filter(status='convertido').count()

    taxa_conversao = 0
    if total_leads > 0:
        taxa_conversao = (leads_convertidos / total_leads) * 100

    # Agrupando leads por fonte para o gráfico
    leads_por_fonte = (
        Lead.objects.values('fonte')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # Agrupando leads por status para outro gráfico
    leads_por_status = (
        Lead.objects.values('status')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # Últimos 5 leads adicionados
    ultimos_leads = Lead.objects.order_by('-data_criacao')[:5]

    fontes_labels = json.dumps([item['fonte'] or 'Não especificado' for item in leads_por_fonte])
    fontes_data = json.dumps([item['total'] for item in leads_por_fonte])

    status_labels = json.dumps([item['status'].replace('_', ' ').title() for item in leads_por_status])
    status_data = json.dumps([item['total'] for item in leads_por_status])

    contexto = {
        'total_leads': total_leads,
        'leads_convertidos': leads_convertidos,
        'taxa_conversao': round(taxa_conversao, 2),
        'fontes_labels': fontes_labels,
        'fontes_data': fontes_data,
        'status_labels': status_labels,
        'status_data': status_data,
        'ultimos_leads': ultimos_leads,
        "add_lead_form": LeadForm(),
    }

    return render(request, 'leads/dashboard_leads.html', contexto)


@login_required
def lead_listar(request):
    nome = request.GET.get("nome", "")
    curso = request.GET.get("curso", "")
    contato = request.GET.get("contato", "")
    status = request.GET.get("status", "")
    
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")

    leads = Lead.objects.all()

    if nome:
        leads = leads.filter(nome_interessado__icontains=nome)
    if curso:
        leads = leads.filter(curso_interesse__icontains=curso)
    if contato:
        leads = leads.filter(contato__icontains=contato)
    if status:
        leads = leads.filter(status=status)

    if data_inicial_str:
        try:
            data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%d').date()
            leads = leads.filter(data_criacao__date__gte=data_inicial)
        except ValueError:
            pass
    
    if data_final_str:
        try:
            data_final = datetime.strptime(data_final_str, '%Y-%m-%d').date()
            leads = leads.filter(data_criacao__date__lte=data_final)
        except ValueError:
            pass

    leads = leads.order_by("-data_criacao")

    paginator = Paginator(leads, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    contexto = {
        "page_obj": page_obj,
        "add_lead_form": LeadForm(),
        "form": LeadForm(),
        "nome": nome,
        "curso": curso,
        "contato": contato,
        "status_selecionado": status,
        "status_choices": Lead.STATUS_CHOICES,
        "data_inicial": data_inicial_str,
        "data_final": data_final_str,
    }

    return render(request, "leads/lead_list.html", contexto)


@login_required
def lead_criar(request):
    if request.method == "POST":
        form = LeadForm(request.POST)
        if form.is_valid():
            form.save()
            # Se a requisição for AJAX (do modal), retorna sucesso em JSON
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})
            # Se for uma requisição normal, redireciona como antes
            messages.success(request, "Lead criado com sucesso!")
            return redirect("leads:lead_listar")
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    
    # Para o GET, a lógica não muda
    form = LeadForm()
    contexto = {"form": form, "titulo": "Adicionar Novo Lead"}
    return render(request, "leads/lead_form.html", contexto)


# --- VIEW CHAVE PARA O PASSO 3 ---
@login_required
def converter_lead(request, pk):
    lead = get_object_or_404(Lead, pk=pk)

    if lead.status == "convertido":
        messages.warning(request, "Este lead já foi convertido.")
        return redirect("leads:lead_listar")

    # Prepara os dados para passar via URL
    # Adapte os nomes dos campos se o seu AlunoForm for diferente
    params = {
        "lead_id": lead.id,
        "nome_completo": lead.nome_interessado,
        'responsavel_nome': lead.nome_responsavel or '',
        # Supondo que o campo de contato possa ser email ou telefone
        "email": lead.contato if "@" in lead.contato else "",
        "telefone": lead.contato if "@" not in lead.contato else "",
    }

    # Monta a URL para a criação de aluno com os parâmetros
    url_destino = f"{reverse('scheduler:aluno_criar')}?{urlencode(params)}"

    return redirect(url_destino)


@login_required
def lead_detalhe(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    
    # Lógica para adicionar uma nova interação
    if request.method == "POST":
        form_interacao = InteracaoLeadForm(request.POST)
        if form_interacao.is_valid():
            nova_interacao = form_interacao.save(commit=False)
            nova_interacao.lead = lead
            nova_interacao.responsavel = request.user
            nova_interacao.save()

            # Atualizar status para 'em_contato' se ainda for 'novo'
            if lead.status == 'novo':
                lead.status = 'em_contato'
                lead.save()

            messages.success(request, "Interação registrada com sucesso!")
            return redirect("leads:lead_detalhe", pk=lead.pk)
    else:
        form_interacao = InteracaoLeadForm()

    # Buscando todas as interações já existentes para este lead
    interacoes = lead.interacoes.all()

    contexto = {
        "lead": lead,
        "interacoes": interacoes,
        "form_interacao": form_interacao,
    }
    return render(request, "leads/lead_detalhe.html", contexto)


def captura_lead_publica(request):
    if request.method == 'POST':
        form = PublicLeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            # Definimos os valores padrão aqui, no backend
            lead.status = 'novo'
            lead.fonte = 'Formulário do Site' # Exemplo de fonte automática
            lead.save()
            return redirect('leads:captura_sucesso')
    else:
        form = PublicLeadForm()

    return render(request, 'leads/captura_lead.html', {'form': form})


# --- VIEW DA PÁGINA DE SUCESSO ---
def captura_sucesso(request):
    return render(request, 'leads/captura_sucesso.html')


@login_required
def kanban_board(request):
    # Definimos os status que queremos como colunas
    status_list = ['novo', 'em_contato', 'negociando']
    
    # Vamos criar uma estrutura mais completa para o template
    kanban_columns = []
    for status in status_list:
        # Aqui fazemos a formatação do título em Python
        display_name = status.replace('_', ' ').title()
        
        leads_in_status = Lead.objects.filter(status=status).order_by('data_criacao')
        
        kanban_columns.append({
            'id': status,
            'name': display_name,
            'leads': leads_in_status,
        })

    contexto = {
        'kanban_columns': kanban_columns,
        "add_lead_form": LeadForm(),
    }
    return render(request, 'leads/kanban_board.html', contexto)


# --- VIEW PARA ATUALIZAR O STATUS VIA JAVASCRIPT ---
@require_POST
@login_required
def update_lead_status(request):
    try:
        data = json.loads(request.body)
        lead_id = int(data.get('lead_id'))
        new_status = data.get('new_status')

        lead = Lead.objects.get(pk=lead_id)
        lead.status = new_status
        lead.save()

        return JsonResponse({'status': 'success', 'message': f'Status do lead {lead_id} atualizado para {new_status}.'})
    except (Lead.DoesNotExist, json.JSONDecodeError, TypeError, ValueError) as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def lead_edit(request, pk):
    lead = get_object_or_404(Lead, pk=pk)

    if lead.status == 'convertido':
        return JsonResponse({
            'status': 'error',
            'message': 'Não é possível editar um lead que já foi convertido em aluno.'
        }, status=403)

    if request.method == 'POST':
        form = LeadForm(request.POST, instance=lead)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    
    # Se for GET, retorna os dados do lead como JSON para preencher o modal
    data = {
        'nome_interessado': lead.nome_interessado,
        'nome_responsavel': lead.nome_responsavel,
        'contato': lead.contato,
        'idade': lead.idade,
        'status': lead.status,
        'curso_interesse': lead.curso_interesse,
        'nivel_experiencia': lead.nivel_experiencia,
        'melhor_horario_contato': lead.melhor_horario_contato,
        'fonte': lead.fonte,
        'observacoes': lead.observacoes,
    }
    return JsonResponse(data)


# --- NOVA VIEW PARA DELETAR O LEAD ---
@login_required
def lead_delete(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if request.method == 'POST':
        lead.delete()
        messages.success(request, "Lead excluído com sucesso!")
        return redirect('leads:lead_listar')
    