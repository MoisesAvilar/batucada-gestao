from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Aula, Aluno, RelatorioAula, Modalidade, CustomUser, PresencaAluno
# --- IMPORTS ATUALIZADOS ---
from django.forms import formset_factory
from .forms import (
    AlunoForm,
    AlunoChoiceForm,
    AulaForm,
    ModalidadeForm,
    ProfessorForm,
    ProfessorChoiceForm,
    RelatorioAulaForm,      # O formulário principal, agora menor
    ItemRudimentoFormSet,   # O novo formset de rudimentos
    ItemRitmoFormSet,       # O novo formset de ritmo
    ItemViradaFormSet,       # O novo formset de viradas
    UserProfileForm,
    PresencaAlunoFormSet
)
from django.contrib import messages
import calendar
from datetime import datetime
from django.utils import timezone
from django.db.models import Count, Min, Case, When, Q, OuterRef, Subquery, F
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
import csv

# --- NOVOS IMPORTS PARA O EXCEL ---
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter


# --- Funções de Teste para Permissões ---
def is_admin(user):
    return user.is_authenticated and user.tipo == "admin"


# --- Função auxiliar para verificar conflitos (NÃO É UMA VIEW) ---
def _check_conflito_aula(professor_ids, data_hora, aula_id=None):
    # ... (Implementação anterior que aceita lista de IDs está correta) ...
    if not professor_ids:
        return {"conflito": False, "mensagem": "Horário disponível."}
    aulas_conflitantes = Aula.objects.filter(professores__id__in=professor_ids, data_hora=data_hora)
    if aula_id:
        aulas_conflitantes = aulas_conflitantes.exclude(pk=aula_id)
    if aulas_conflitantes.exists():
        # ... (lógica de mensagem de erro) ...
        return {"conflito": True, "mensagem": "Conflito de horário detectado."}
    return {"conflito": False, "mensagem": "Horário disponível."}


# --- Views Principais (dashboard) ---
# scheduler/views.py

@login_required
def dashboard(request):
    now = timezone.now()
    today = now.date()
    next_week = today + timezone.timedelta(days=7)
    
    # --- LÓGICA PARA O DASHBOARD DO ADMIN (sem alterações) ---
    if request.user.tipo == 'admin':
        mes_atual = today.month
        ano_atual = today.year
        primeiro_dia_mes = today.replace(day=1)
        ultimo_dia_mes = today.replace(day=calendar.monthrange(ano_atual, mes_atual)[1])


        aulas_hoje_count = Aula.objects.filter(data_hora__date=today).exclude(status__in=['Cancelada', 'Aluno Ausente']).count()
        aulas_semana_count = Aula.objects.filter(data_hora__date__range=[today, next_week]).count()
        aulas_agendadas_total = Aula.objects.filter(status='Agendada', data_hora__gte=now).count()
        novos_alunos_mes = Aluno.objects.filter(
            data_criacao__year=ano_atual,
            data_criacao__month=mes_atual
        ).count()

        aulas_do_dia = Aula.objects.filter(data_hora__date=today).order_by('data_hora').prefetch_related('alunos', 'professores')
        aulas_da_semana = Aula.objects.filter(data_hora__date__range=[today, next_week]).order_by('data_hora').prefetch_related('alunos', 'professores')
        
        professores_list = CustomUser.objects.filter(tipo__in=["professor", "admin"]).order_by("username")

        aula_form_modal = AulaForm()
        aluno_formset_modal = formset_factory(AlunoChoiceForm, extra=1, can_delete=True)(prefix='alunos')
        professor_formset_modal = formset_factory(ProfessorChoiceForm, extra=1, can_delete=True)(prefix='professores')

        
        contexto = {
            "titulo": "Dashboard do Administrador",
            "today": today,
            "novos_alunos_mes": novos_alunos_mes,
            "primeiro_dia_mes": primeiro_dia_mes.strftime('%Y-%m-%d'),
            "ultimo_dia_mes": ultimo_dia_mes.strftime('%Y-%m-%d'),
            "aulas_hoje_count": aulas_hoje_count,
            "aulas_semana_count": aulas_semana_count,
            "aulas_agendadas_total": aulas_agendadas_total,
            "aulas_do_dia": aulas_do_dia,
            "aulas_da_semana": aulas_da_semana,
            "professores_list": professores_list,

            "aula_form_modal": aula_form_modal,
            "aluno_formset_modal": aluno_formset_modal,
            "professor_formset_modal": professor_formset_modal,
            "form_action_modal": reverse('scheduler:aula_agendar'),
        }
    
    # --- LÓGICA PARA O DASHBOARD DO PROFESSOR (CORRIGIDA) ---
    else: # Se não é admin, é professor
        # --- CORREÇÃO AQUI ---
        # A consulta agora usa 'professores' (plural) para o ManyToManyField.
        aulas_do_professor = Aula.objects.filter(
            Q(professores=request.user) | Q(relatorioaula__professor_que_validou=request.user)
        ).distinct().prefetch_related('alunos', 'professores')

        # KPIs do Professor
        aulas_hoje_count = aulas_do_professor.filter(data_hora__date=today).count()
        aulas_semana_count = aulas_do_professor.filter(data_hora__date__range=[today, next_week]).count()
        aulas_pendentes_count = aulas_do_professor.filter(status='Agendada', data_hora__lt=now).count()

        # Listas para o Professor
        aulas_do_dia = aulas_do_professor.filter(data_hora__date=today).order_by('data_hora')
        proximas_aulas_semana = aulas_do_professor.filter(status='Agendada', data_hora__gte=now, data_hora__date__lte=next_week).order_by('data_hora')
        aulas_pendentes_validacao = aulas_do_professor.filter(status='Agendada', data_hora__lt=now).order_by('data_hora')

        contexto = {
            "titulo": "Meu Dashboard",
            "today": today,
            "aulas_hoje_count": aulas_hoje_count,
            "aulas_semana_count": aulas_semana_count,
            "aulas_pendentes_count": aulas_pendentes_count,
            "aulas_do_dia": aulas_do_dia,
            "proximas_aulas_semana": proximas_aulas_semana,
            "aulas_pendentes_validacao": aulas_pendentes_validacao,
        }

    return render(request, "scheduler/dashboard.html", contexto)


# --- Views de Aulas (agendar_aula, editar_aula, excluir_aula) ---
@user_passes_test(is_admin)
def agendar_aula(request):
    """
    View para agendar novas aulas. Suporta agendamento simples, recorrente
    e envio de formulário via AJAX a partir de um modal.
    """
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    AlunoFormSet = formset_factory(AlunoChoiceForm, extra=1, can_delete=True)
    ProfessorFormSet = formset_factory(ProfessorChoiceForm, extra=1, can_delete=True)

    if request.method == 'POST':
        form = AulaForm(request.POST)
        aluno_formset = AlunoFormSet(request.POST, prefix='alunos')
        professor_formset = ProfessorFormSet(request.POST, prefix='professores')

        # Verifica a validade de todos os formulários e formsets
        if form.is_valid() and aluno_formset.is_valid() and professor_formset.is_valid():
            modalidade = form.cleaned_data.get('modalidade')
            status = form.cleaned_data.get('status')
            alunos_ids = {f['aluno'].id for f in aluno_formset.cleaned_data if f and not f.get('DELETE')}
            professores_ids = {f['professor'].id for f in professor_formset.cleaned_data if f and not f.get('DELETE')}
            data_hora_inicial = form.cleaned_data.get('data_hora')
            is_recorrente = form.cleaned_data.get('recorrente_mensal')

            # Lógica para calcular as datas de agendamento
            datas_para_agendar = []
            if is_recorrente:
                dia_semana = data_hora_inicial.weekday()
                mes, ano = data_hora_inicial.month, data_hora_inicial.year
                cal = calendar.Calendar()
                for dia in cal.itermonthdates(ano, mes):
                    if dia.month == mes and dia.weekday() == dia_semana and dia >= data_hora_inicial.date():
                        datas_para_agendar.append(data_hora_inicial.replace(year=dia.year, month=dia.month, day=dia.day))
            else:
                datas_para_agendar.append(data_hora_inicial)

            # Validação de conflitos
            conflitos_encontrados = []
            for data_agendamento in datas_para_agendar:
                conflito_info = _check_conflito_aula(list(professores_ids), data_agendamento)
                if conflito_info['conflito']:
                    mensagem = conflito_info.get('mensagem', 'Conflito de horário')
                    conflitos_encontrados.append(f"{mensagem} na data {data_agendamento.strftime('%d/%m')}.")
            
            if conflitos_encontrados:
                if is_ajax:
                    return JsonResponse({'success': False, 'errors': conflitos_encontrados}, status=400)
                for erro in conflitos_encontrados:
                    messages.error(request, erro)
            else:
                # Se não houver conflitos, salva as aulas
                aulas_criadas_count = 0
                for data_agendamento in datas_para_agendar:
                    nova_aula = Aula.objects.create(modalidade=modalidade, data_hora=data_agendamento, status=status)
                    nova_aula.alunos.set(list(alunos_ids))
                    nova_aula.professores.set(list(professores_ids))
                    aulas_criadas_count += 1
                
                message_text = f'{aulas_criadas_count} aulas recorrentes foram agendadas.' if aulas_criadas_count > 1 else 'Aula agendada com sucesso!'
                if is_ajax:
                    return JsonResponse({'success': True, 'message': message_text})
                
                messages.success(request, message_text)
                return redirect('scheduler:dashboard')
        else:
            # --- SE O FORMULÁRIO FOR INVÁLIDO ---
            if is_ajax:
                error_list = []
                for field, errors in form.errors.items():
                    error_list.append(f"{field.replace('_', ' ').title()}: {errors[0]}")
                for fs_form in aluno_formset:
                    for field, errors in fs_form.errors.items(): error_list.append(f"Aluno: {errors[0]}")
                for fs_form in professor_formset:
                    for field, errors in fs_form.errors.items(): error_list.append(f"Professor: {errors[0]}")
                
                if not error_list: error_list.append("Por favor, verifique os dados inseridos.")
                return JsonResponse({'success': False, 'errors': error_list}, status=400)
            
            # Para POST normal, exibe a mensagem de erro e re-renderiza a página
            messages.error(request, 'Erro ao agendar a aula. Verifique os campos marcados.')

    # Lógica para requisições GET ou para renderizar a página com erros de um POST normal
    form = AulaForm()
    aluno_formset = AlunoFormSet(prefix='alunos')
    professor_formset = ProfessorFormSet(prefix='professores')
    contexto = {
        'form': form,
        'aluno_formset': aluno_formset,
        'professor_formset': professor_formset,
        'titulo': 'Agendar Nova Aula',
        'form_action': reverse('scheduler:aula_agendar')
    }
    return render(request, 'scheduler/aula_form.html', contexto)

@user_passes_test(is_admin)
def editar_aula(request, pk):
    aula = get_object_or_404(Aula, pk=pk)
    AlunoFormSet = formset_factory(AlunoChoiceForm, extra=1, can_delete=True)
    ProfessorFormSet = formset_factory(ProfessorChoiceForm, extra=1, can_delete=True)

    if request.method == 'POST':
        form = AulaForm(request.POST, instance=aula)
        aluno_formset = AlunoFormSet(request.POST, prefix='alunos')
        professor_formset = ProfessorFormSet(request.POST, prefix='professores')

        if form.is_valid() and aluno_formset.is_valid() and professor_formset.is_valid():
            # Coleta os dados dos formulários
            alunos_ids = {f['aluno'].id for f in aluno_formset.cleaned_data if f and not f.get('DELETE')}
            professores_ids = {f['professor'].id for f in professor_formset.cleaned_data if f and not f.get('DELETE')}
            data_hora_nova = form.cleaned_data.get('data_hora')
            is_recorrente = form.cleaned_data.get('recorrente_mensal')

            # --- LÓGICA DE RECORRÊNCIA NA EDIÇÃO ---

            # 1. Verifica conflito para a aula principal que está sendo editada
            conflito_info_principal = _check_conflito_aula(list(professores_ids), data_hora_nova, aula_id=aula.pk)
            if conflito_info_principal['conflito']:
                messages.error(request, f"Não foi possível atualizar a aula: {conflito_info_principal['mensagem']}")
            else:
                # Se a aula principal está OK, salva as alterações nela
                aula_salva = form.save()
                aula_salva.alunos.set(list(alunos_ids))
                aula_salva.professores.set(list(professores_ids))
                
                # 2. Se a checkbox de recorrência estiver marcada, cria as aulas seguintes
                if is_recorrente:
                    datas_para_agendar = []
                    dia_semana = data_hora_nova.weekday()
                    mes, ano = data_hora_nova.month, data_hora_nova.year
                    cal = calendar.Calendar()
                    
                    for dia in cal.itermonthdates(ano, mes):
                        # Adiciona apenas as datas que são no mesmo mês, mesmo dia da semana, e POSTERIORES à data atual
                        if dia.month == mes and dia.weekday() == dia_semana and dia > data_hora_nova.date():
                            nova_data_hora = data_hora_nova.replace(year=dia.year, month=dia.month, day=dia.day)
                            datas_para_agendar.append(nova_data_hora)

                    # 3. Verifica conflitos para as NOVAS aulas recorrentes
                    conflitos_novos = [info['mensagem'] for dt in datas_para_agendar if (info := _check_conflito_aula(list(professores_ids), dt))['conflito']]

                    if conflitos_novos:
                        messages.warning(request, f"A aula do dia {data_hora_nova.strftime('%d/%m')} foi atualizada, mas as aulas recorrentes não puderam ser criadas devido a conflitos.")
                        for erro in conflitos_novos:
                            messages.error(request, erro)
                    else:
                        # 4. Cria as novas aulas recorrentes
                        aulas_criadas_count = 0
                        for data_agendamento in datas_para_agendar:
                            nova_aula = Aula.objects.create(
                                modalidade=aula_salva.modalidade, data_hora=data_agendamento, status=aula_salva.status
                            )
                            nova_aula.alunos.set(list(alunos_ids))
                            nova_aula.professores.set(list(professores_ids))
                            aulas_criadas_count += 1
                        
                        if aulas_criadas_count > 0:
                            messages.success(request, f"Aula principal atualizada e {aulas_criadas_count} novas aulas recorrentes foram agendadas!")
                        else:
                            messages.success(request, 'Aula atualizada com sucesso!')
                else:
                    messages.success(request, 'Aula atualizada com sucesso!')
                
                return redirect('scheduler:dashboard')

    else: # GET
        form = AulaForm(instance=aula)
        alunos_data = [{'aluno': aluno_obj} for aluno_obj in aula.alunos.all()]
        professores_data = [{'professor': prof_obj} for prof_obj in aula.professores.all()]
        aluno_formset = AlunoFormSet(initial=alunos_data, prefix='alunos')
        professor_formset = ProfessorFormSet(initial=professores_data, prefix='professores')

    contexto = {
        'form': form, 'aula': aula, 'aluno_formset': aluno_formset,
        'professor_formset': professor_formset, 'titulo': 'Editar Aula',
        'form_action': reverse('scheduler:aula_editar', kwargs={'pk': aula.pk})
    }
    return render(request, 'scheduler/aula_form.html', contexto)


@user_passes_test(is_admin)
def excluir_aula(request, pk):
    aula = get_object_or_404(Aula, pk=pk)
    if request.method == "POST":
        aula.delete()
        messages.success(request, "Aula excluída com sucesso!")
        return redirect("scheduler:dashboard")
    return render(request, "scheduler/aula_confirm_delete.html", {"aula": aula})


# scheduler/views.py

@login_required
@user_passes_test(lambda u: u.tipo in ['admin', 'professor'])
def aulas_para_substituir(request):
    """
    Mostra uma lista de aulas futuras agendadas para outros professores,
    disponíveis para substituição.
    """
    now = timezone.now()
    # --- CORRIGIDO: Exclui aulas onde o professor logado está na lista de 'professores' ---
    aulas_disponiveis = Aula.objects.filter(
        data_hora__gte=now,
        status='Agendada'
    ).exclude(
        professores=request.user
    ).order_by('data_hora')

    paginator = Paginator(aulas_disponiveis, 10)
    aulas = paginator.get_page(request.GET.get('page'))

    contexto = {'titulo': 'Aulas Disponíveis para Substituição', 'aulas': aulas}
    return render(request, 'scheduler/aulas_para_substituir.html', contexto)


# --- VIEWS DE GERENCIAMENTO DE ALUNOS ---
@login_required
def listar_alunos(request):
    search_query = request.GET.get("q", "")
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")
    now = timezone.now()

    if request.user.tipo == 'professor':
        alunos_queryset = Aluno.objects.filter(aulas_aluno__professores=request.user).distinct().annotate(
            total_aulas=Count('aulas_aluno', filter=Q(aulas_aluno__professores=request.user)),
            proxima_aula=Min(
                Case(
                    When(
                        aulas_aluno__data_hora__gte=now,
                        aulas_aluno__professores=request.user,
                        then='aulas_aluno__data_hora'
                    ),
                    default=None
                )
            )
        )
    else: # Visão do Admin
        alunos_queryset = Aluno.objects.all().annotate(
            total_aulas=Count('aulas_aluno'),
            proxima_aula=Min(
                Case(
                    When(aulas_aluno__data_hora__gte=now, then='aulas_aluno__data_hora'),
                    default=None
                )
            )
        )

    if search_query:
        alunos_queryset = alunos_queryset.filter(
            Q(nome_completo__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(telefone__icontains=search_query)
        ).distinct()

    if data_inicial_str:
        try:
            data_inicial = datetime.strptime(data_inicial_str, "%Y-%m-%d").date()
            alunos_queryset = alunos_queryset.filter(data_criacao__gte=data_inicial)
        except ValueError:
            pass # Ignora data inválida
    
    if data_final_str:
        try:
            data_final = datetime.strptime(data_final_str, "%Y-%m-%d").date()
            alunos_queryset = alunos_queryset.filter(data_criacao__lte=data_final)
        except ValueError:
            pass # Ignora data inválida

    alunos = alunos_queryset.order_by("nome_completo")

    contexto = {
        "alunos": alunos,
        "titulo": "Gerenciamento de Alunos",
        "search_query": search_query,
        "data_inicial": data_inicial_str,
        "data_final": data_final_str,
    }
    return render(request, "scheduler/aluno_listar.html", contexto)

@user_passes_test(is_admin)
def criar_aluno(request):
    if request.method == "POST":
        form = AlunoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Aluno criado com sucesso!")
            return redirect("scheduler:aluno_listar")
    else:
        form = AlunoForm()
    contexto = {"form": form, "titulo": "Adicionar Novo Aluno"}
    return render(
        request,
        "scheduler/aluno_form.html",
        contexto,
    )


@user_passes_test(is_admin)
def editar_aluno(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    if request.method == "POST":
        form = AlunoForm(request.POST, instance=aluno)
        if form.is_valid():
            form.save()
            messages.success(request, "Aluno atualizada com sucesso!")
            return redirect("scheduler:aluno_listar")
    else:
        form = AlunoForm(instance=aluno)
    contexto = {"form": form, "titulo": "Editar Aluno"}
    return render(request, "scheduler/aluno_form.html", contexto)


@user_passes_test(is_admin)
def excluir_aluno(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    if request.method == "POST":
        aluno.delete()
        messages.success(request, "Aluno excluído com sucesso!")
        return redirect("scheduler:aluno_listar")
    contexto = {"aluno": aluno}
    return render(request, "scheduler/aluno_confirm_delete.html", contexto)


# --- VISÃO DE DETALHE DO ALUNO ---
@login_required
def detalhe_aluno(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    
    # --- LÓGICA DE CONSULTA APRIMORADA ---
    # Subquery para buscar o status de presença individual do aluno para cada aula
    presenca_status_subquery = PresencaAluno.objects.filter(
        aula=OuterRef('pk'),
        aluno=aluno
    ).values('status')[:1]

    # Anota o status de presença na consulta principal de aulas
    aulas_do_aluno = Aula.objects.filter(alunos=aluno).annotate(
        status_presenca_aluno=Subquery(presenca_status_subquery)
    ).order_by("-data_hora")

    # A lógica de cálculo dos KPIs permanece a mesma que corrigimos antes
    presencas_do_aluno = PresencaAluno.objects.filter(aluno=aluno)
    total_realizadas = presencas_do_aluno.filter(status="presente").count()
    total_aluno_ausente = presencas_do_aluno.filter(status="ausente").count()
    total_aulas = aulas_do_aluno.count()
    total_canceladas = aulas_do_aluno.filter(status="Cancelada").count()
    total_agendadas = aulas_do_aluno.filter(status="Agendada").count()
    aulas_contabilizaveis_presenca = total_realizadas + total_aluno_ausente
    taxa_presenca = (total_realizadas / aulas_contabilizaveis_presenca * 100) if aulas_contabilizaveis_presenca > 0 else 0
    top_professores = aulas_do_aluno.filter(professores__isnull=False).values("professores__pk", "professores__username").annotate(contagem=Count("professores__pk")).order_by("-contagem")[:3]
    top_modalidades = aulas_do_aluno.values("modalidade__nome").annotate(contagem=Count("modalidade")).order_by("-contagem")[:3]
    
    aulas_do_aluno_paginated = Paginator(aulas_do_aluno, 10).get_page(request.GET.get("page"))

    contexto = {
        "aluno": aluno,
        "aulas_do_aluno": aulas_do_aluno_paginated,
        "titulo": f"Perfil do Aluno: {aluno.nome_completo}",
        "total_aulas": total_aulas,
        "total_realizadas": total_realizadas,
        "total_canceladas": total_canceladas,
        "total_aluno_ausente": total_aluno_ausente,
        "total_agendadas": total_agendadas,
        "taxa_presenca": taxa_presenca,
        "top_professores": top_professores,
        "top_modalidades": top_modalidades,
    }
    return render(request, "scheduler/aluno_detalhe.html", contexto)


@login_required
def listar_aulas(request):
    # 1. Obtenção de todos os filtros da URL
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")
    professor_filtro_id = request.GET.get("professor_filtro", "")
    modalidade_filtro_id = request.GET.get("modalidade_filtro", "")
    status_filtro = request.GET.get("status_filtro", "")
    aluno_filtro_ids = request.GET.getlist("aluno_filtro")
    
    # 2. Definição do queryset base
    if request.user.tipo == "admin":
        aulas_queryset = Aula.objects.all()
        contexto_titulo = "Histórico Geral de Aulas"
    else:  # Professor
        aulas_queryset = Aula.objects.filter(
            Q(professores=request.user) | Q(relatorioaula__professor_que_validou=request.user)
        ).distinct()
        contexto_titulo = "Meu Histórico de Aulas"

    # 3. Aplicação de todos os filtros
    if data_inicial_str:
        try: aulas_queryset = aulas_queryset.filter(data_hora__date__gte=datetime.strptime(data_inicial_str, "%Y-%m-%d").date())
        except ValueError: pass
    if data_final_str:
        try: aulas_queryset = aulas_queryset.filter(data_hora__date__lte=datetime.strptime(data_final_str, "%Y-%m-%d").date())
        except ValueError: pass
    if professor_filtro_id:
        aulas_queryset = aulas_queryset.filter(Q(professores__id=professor_filtro_id) | Q(relatorioaula__professor_que_validou__id=professor_filtro_id))
    if modalidade_filtro_id:
        aulas_queryset = aulas_queryset.filter(modalidade_id=modalidade_filtro_id)
    if status_filtro:
        if status_filtro == 'Substituído':
            aulas_queryset = aulas_queryset.filter(
                status='Realizada', professores__isnull=False, relatorioaula__professor_que_validou__isnull=False
            ).exclude(professores=F('relatorioaula__professor_que_validou'))
        else:
            aulas_queryset = aulas_queryset.filter(status=status_filtro)

    if aluno_filtro_ids:
        # Garante que os valores sejam inteiros para a consulta
        aluno_filtro_ids = [int(id) for id in aluno_filtro_ids if id.isdigit()]
        if aluno_filtro_ids:
            aulas_queryset = aulas_queryset.filter(alunos__id__in=aluno_filtro_ids).distinct()
 
            
    aulas_ordenadas = aulas_queryset.order_by("-data_hora").prefetch_related('alunos', 'professores', 'relatorioaula__professor_que_validou')
    
    # Paginação
    paginator = Paginator(aulas_ordenadas, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    # --- CORREÇÃO AQUI ---
    # Adicionamos a lista de professores e outras listas necessárias para os filtros no contexto
    contexto = {
        "aulas": page_obj,
        "titulo": contexto_titulo,
        "data_inicial": data_inicial_str,
        "data_final": data_final_str,
        "professor_filtro": professor_filtro_id,
        "modalidade_filtro": modalidade_filtro_id,
        "status_filtro": status_filtro,
        "professores_list": CustomUser.objects.filter(tipo__in=["professor", "admin"]).order_by("username"),
        "modalidades_list": Modalidade.objects.all().order_by("nome"),
        "alunos_list": Aluno.objects.all().order_by("nome_completo"),
        "status_choices": Aula.STATUS_AULA_CHOICES,
    }
    return render(request, "scheduler/aula_listar.html", contexto)


@login_required
@user_passes_test(lambda u: u.tipo in ['admin', 'professor'])
def validar_aula(request, pk):
    aula = get_object_or_404(Aula, pk=pk)
    relatorio, created = RelatorioAula.objects.get_or_create(aula=aula)

    # --- INÍCIO DA LÓGICA DE HISTÓRICO CORRIGIDA ---
    historico_ultima_aula = None
    ultima_aula = None # Variável para armazenar a aula encontrada
    alunos_da_aula = aula.alunos.all()

    if alunos_da_aula.exists():
        # Se a aula tem alunos, busca a última aula do mesmo grupo.
        ultima_aula = Aula.objects.filter(
            alunos__in=alunos_da_aula, 
            status__in=['Realizada', 'Aluno Ausente'],
            data_hora__lt=aula.data_hora,
            relatorioaula__isnull=False
        ).distinct().order_by('-data_hora').first()
    else:
        # Se NÃO tem alunos (Atividade Complementar), busca a última aula da mesma modalidade.
        ultima_aula = Aula.objects.filter(
            modalidade=aula.modalidade,
            status='Realizada',
            data_hora__lt=aula.data_hora,
            relatorioaula__isnull=False
        ).order_by('-data_hora').first()
        
    if ultima_aula:
        historico_ultima_aula = ultima_aula.relatorioaula
    # --- FIM DA LÓGICA DE HISTÓRICO CORRIGIDA ---

    # --- LÓGICA DA LISTA DE PRESENÇA (sem alterações) ---
    # Se a aula tem alunos, garante que um registro de presença exista para cada um.
    if alunos_da_aula.exists():
        for aluno in alunos_da_aula:
            PresencaAluno.objects.get_or_create(aula=aula, aluno=aluno)
    
    # Cria o queryset de presença para esta aula específica
    presenca_queryset = PresencaAluno.objects.filter(aula=aula).order_by('aluno__nome_completo')

    # Lógica para determinar o modo de visualização (sem alterações)
    url_mode = request.GET.get('mode')
    view_mode = "editar" if aula.status == "Agendada" else url_mode if url_mode in ["visualizar", "editar"] else "visualizar"

    if request.method == 'POST':
        form = RelatorioAulaForm(request.POST, instance=relatorio)
        presenca_formset = PresencaAlunoFormSet(request.POST, queryset=presenca_queryset, prefix='presencas')
        rudimentos_formset = ItemRudimentoFormSet(request.POST, instance=relatorio, prefix='rudimentos')
        ritmo_formset = ItemRitmoFormSet(request.POST, instance=relatorio, prefix='ritmo')
        viradas_formset = ItemViradaFormSet(request.POST, instance=relatorio, prefix='viradas')

        # Valida todos os formulários e formsets (sem alterações)
        if all([f.is_valid() for f in [form, presenca_formset, rudimentos_formset, ritmo_formset, viradas_formset]]):
            
            # Salva tudo (sem alterações)
            relatorio.professor_que_validou = request.user
            form.save()
            rudimentos_formset.save()
            ritmo_formset.save()
            viradas_formset.save()
            presenca_formset.save()

            # --- LÓGICA DE ATUALIZAÇÃO DE STATUS DA AULA (sem alterações) ---
            num_presentes = PresencaAluno.objects.filter(aula=aula, status='presente').count()
            
            if alunos_da_aula.exists() and num_presentes == 0:
                aula.status = 'Aluno Ausente'
            else:
                aula.status = 'Realizada'
            aula.save()

            messages.success(request, 'Relatório da aula salvo e presenças registradas com sucesso!')
            return redirect('scheduler:aula_listar')
        else:
            messages.error(request, 'Erro ao salvar o relatório. Verifique os campos marcados.')
    
    else: # GET (sem alterações)
        form = RelatorioAulaForm(instance=relatorio)
        presenca_formset = PresencaAlunoFormSet(queryset=presenca_queryset, prefix='presencas')
        rudimentos_formset = ItemRudimentoFormSet(instance=relatorio, prefix='rudimentos')
        ritmo_formset = ItemRitmoFormSet(instance=relatorio, prefix='ritmo')
        viradas_formset = ItemViradaFormSet(instance=relatorio, prefix='viradas')

    context = {
        'aula': aula, 'relatorio': relatorio, 'form': form,
        'presenca_formset': presenca_formset,
        'rudimentos_formset': rudimentos_formset,
        'ritmo_formset': ritmo_formset,
        'viradas_formset': viradas_formset,
        'view_mode': view_mode,
        'historico_ultima_aula': historico_ultima_aula,
    }
    return render(request, 'scheduler/aula_validar.html', context)


# --- VIEWS PARA GERENCIAMENTO DE MODALIDADES ---
@user_passes_test(is_admin)
def listar_modalidades(request):
    search_query = request.GET.get("q", "")
    now = timezone.now()
    modalidades_queryset = Modalidade.objects.all()

    modalidades_queryset = modalidades_queryset.annotate(
        total_aulas=Count('aula'),
        # --- CORRIGIDO ---
        # A contagem de alunos ativos agora usa a relação 'aula__alunos'.
        alunos_ativos=Count(
            'aula__alunos', 
            distinct=True, 
            filter=Q(aula__data_hora__gte=now)
        ),
        proxima_aula=Min(Case(When(aula__data_hora__gte=now, then='aula__data_hora'), default=None))
    )

    if search_query:
        modalidades_queryset = modalidades_queryset.filter(nome__icontains=search_query)
    
    modalidades = modalidades_queryset.order_by("nome")

    contexto = {
        "modalidades": modalidades,
        "titulo": "Gerenciamento de Categorias",
        "search_query": search_query,
    }
    return render(request, "scheduler/modalidade_listar.html", contexto)




@user_passes_test(is_admin)
def criar_modalidade(request):
    if request.method == "POST":
        form = ModalidadeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria criada com sucesso!")
            return redirect("scheduler:modalidade_listar")
    else:
        form = ModalidadeForm()
    contexto = {"form": form, "titulo": "Adicionar Nova Categoria"}
    return render(request, "scheduler/modalidade_form.html", contexto)


@user_passes_test(is_admin)
def editar_modalidade(request, pk):
    modalidade = get_object_or_404(Modalidade, pk=pk)
    if request.method == "POST":
        form = ModalidadeForm(request.POST, instance=modalidade)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria atualizada com sucesso!")
            return redirect("scheduler:modalidade_listar")
    else:
        form = ModalidadeForm(instance=modalidade)
    contexto = {"form": form, "titulo": f"Editar Categoria: {modalidade.nome.title()}"}
    return render(request, "scheduler/modalidade_form.html", contexto)


@user_passes_test(is_admin)
def excluir_modalidade(request, pk):
    modalidade = get_object_or_404(Modalidade, pk=pk)
    if modalidade.aula_set.exists():
        messages.error(
            request,
            f'Não é possível excluir a categoria "{modalidade.nome}" porque há aulas associadas a ela. Remova as aulas primeiro.',
        )
        return redirect("scheduler:modalidade_listar")

    if request.method == "POST":
        modalidade.delete()
        messages.success(request, "Categoria excluída com sucesso!")
        return redirect("scheduler:modalidade_listar")
    contexto = {
        "modalidade": modalidade,
        "titulo": f"Confirmar Exclusão de Categoria: {modalidade.nome}",
    }
    return render(request, "scheduler/modalidade_confirm_delete.html", contexto)


@user_passes_test(is_admin)
def detalhe_modalidade(request, pk):
    modalidade = get_object_or_404(Modalidade, pk=pk)
    aulas_da_modalidade = Aula.objects.filter(modalidade=modalidade)
    now = timezone.now()

    # KPIs de Contagem
    total_aulas = aulas_da_modalidade.count()
    total_realizadas = aulas_da_modalidade.filter(status="Realizada").count()
    
    # --- CORRIGIDO ---
    # Contagens de alunos e professores agora usam os campos no plural.
    alunos_ativos_count = aulas_da_modalidade.filter(
        data_hora__gte=now
    ).values('alunos').distinct().count()

    professores_count = aulas_da_modalidade.filter(
        professores__isnull=False
    ).values('professores').distinct().count()

    # --- CORRIGIDO ---
    # A busca reversa de professores agora usa 'aulas_lecionadas' (related_name).
    professores_da_modalidade = CustomUser.objects.filter(
        aulas_lecionadas__in=aulas_da_modalidade
    ).distinct().order_by('username')
    
    # Dados do Gráfico de Atividade Mensal
    aulas_por_mes = aulas_da_modalidade.annotate(
        mes=TruncMonth('data_hora')
    ).values('mes').annotate(
        contagem=Count('id')
    ).order_by('mes')

    chart_labels = [item['mes'].strftime('%b/%Y') for item in aulas_por_mes]
    chart_data = [item['contagem'] for item in aulas_por_mes]
    
    # Paginação
    aulas_paginadas = Paginator(aulas_da_modalidade.order_by("-data_hora").prefetch_related('alunos', 'professores'), 10).get_page(request.GET.get("page"))

    contexto = {
        "modalidade": modalidade,
        "titulo": f"Dashboard da Categoria: {modalidade.nome}",
        "total_aulas": total_aulas,
        "total_realizadas": total_realizadas,
        "alunos_ativos_count": alunos_ativos_count,
        "professores_count": professores_count,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "professores_da_modalidade": professores_da_modalidade,
        "aulas": aulas_paginadas,
    }
    
    return render(request, "scheduler/modalidade_detalhe.html", contexto)

# --- VIEWS PARA GERENCIAMENTO DE PROFESSORES ---
@user_passes_test(is_admin)
def listar_professores(request):
    search_query = request.GET.get("q", "")
    now = timezone.now()

    professores_queryset = CustomUser.objects.filter(tipo__in=['professor', 'admin'])

    proxima_aula_subquery = Aula.objects.filter(
        professores=OuterRef('pk'), 
        data_hora__gte=now
    ).order_by('data_hora').values('data_hora')[:1]

    professores_queryset = professores_queryset.annotate(
        total_aulas_realizadas=Count(
            'aulas_validadas_por_mim',
            filter=Q(aulas_validadas_por_mim__aula__status='Realizada'),
            distinct=True
        ),

        total_alunos_atendidos=Count('aulas_lecionadas__alunos', distinct=True),
        proxima_aula=Subquery(proxima_aula_subquery)
    )

    if search_query:
        professores_queryset = professores_queryset.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    professores = professores_queryset.order_by("username")

    contexto = {
        "professores": professores,
        "titulo": "Gerenciamento de Professores",
        "search_query": search_query,
    }
    return render(request, "scheduler/professor_listar.html", contexto)


@user_passes_test(is_admin)
def editar_professor(request, pk):
    professor = get_object_or_404(CustomUser, pk=pk, tipo__in=["admin", "professor"])
    if request.method == "POST":
        form = ProfessorForm(request.POST, instance=professor)
        form.fields.pop("password", None)
        form.fields.pop("password_confirm", None)

        if form.is_valid():
            form.save()
            messages.success(
                request, f"Professor {professor.username} atualizado com sucesso!"
            )
            return redirect("scheduler:professor_listar")
    else:
        form = ProfessorForm(instance=professor)
        form.fields.pop("password", None)
        form.fields.pop("password_confirm", None)
        # form.fields['tipo'].widget.attrs['disabled'] = True

    contexto = {"form": form, "titulo": f"Editar Professor: {professor.username}"}
    return render(request, "scheduler/professor_form.html", contexto)


@user_passes_test(is_admin)
def excluir_professor(request, pk):
    professor = get_object_or_404(CustomUser, pk=pk)
    # --- CORRIGIDO: Usa o related_name 'aulas_lecionadas' que definimos no modelo ---
    if professor.aulas_lecionadas.exists():
        messages.warning(
            request,
            f'O professor "{professor.username}" está atribuído a {professor.aulas_lecionadas.count()} aulas. Ao excluí-lo, essas aulas ficarão sem professor atribuído.',
        )

    if request.user.pk == pk:
        messages.error(request, "Você não pode excluir seu próprio usuário.")
        return redirect("scheduler:professor_listar")

    if request.method == "POST":
        professor.delete()
        messages.success(request, "Professor excluído com sucesso!")
        return redirect("scheduler:professor_listar")
    contexto = {
        "professor": professor,
        "titulo": f"Confirmar Exclusão de Professor: {professor.username}",
    }
    return render(request, "scheduler/professor_confirm_delete.html", contexto)


# --- VISÃO DE DETALHE DO PROFESSOR ---
@login_required
def detalhe_professor(request, pk):
    # A lógica de permissão está OK
    if not (request.user.tipo == "admin" or (request.user.pk == pk and request.user.tipo == 'professor')):
        messages.error(request, "Você não tem permissão para acessar este perfil.")
        return redirect("scheduler:dashboard")

    professor = get_object_or_404(CustomUser, pk=pk, tipo__in=['professor', 'admin'])
    
    # Lógica de filtro por data (está OK)
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")
    data_inicial, data_final = None, None

    if data_inicial_str:
        try: data_inicial = datetime.strptime(data_inicial_str, "%Y-%m-%d").date()
        except ValueError: pass
    if data_final_str:
        try: data_final = datetime.strptime(data_final_str, "%Y-%m-%d").date()
        except ValueError: pass

    # Queryset base (já estava correto)
    aulas_relacionadas = Aula.objects.filter(
        Q(professores=professor) | Q(relatorioaula__professor_que_validou=professor)
    ).distinct()

    if data_inicial:
        aulas_relacionadas = aulas_relacionadas.filter(data_hora__date__gte=data_inicial)
    if data_final:
        aulas_relacionadas = aulas_relacionadas.filter(data_hora__date__lte=data_final)
    
    # Cálculo dos KPIs
    total_realizadas = aulas_relacionadas.filter(status='Realizada', relatorioaula__professor_que_validou=professor).count()
    total_agendadas = aulas_relacionadas.filter(status='Agendada', professores=professor).count()
    total_canceladas = aulas_relacionadas.filter(status='Cancelada', professores=professor).count()
    total_aluno_ausente = aulas_relacionadas.filter(status='Aluno Ausente', professores=professor).count()

    # --- CORREÇÃO AQUI ---
    # O filtro agora usa 'professores' (plural) para encontrar as aulas atribuídas ao professor.
    total_substituido = aulas_relacionadas.filter(
        status='Realizada',
        professores=professor  # Aulas que foram ATRIBUÍDAS a ele
    ).exclude(
        relatorioaula__professor_que_validou=professor # ...mas NÃO foram realizadas por ele.
    ).count()

    # O resto da view (Top alunos, Top modalidades, etc.) já estava correto.
    aulas_contabilizaveis_presenca = total_realizadas + total_aluno_ausente
    taxa_presenca = (total_realizadas / aulas_contabilizaveis_presenca * 100) if aulas_contabilizaveis_presenca > 0 else 0

    top_alunos = (
        aulas_relacionadas.filter(alunos__isnull=False)
        .values("alunos__pk", "alunos__nome_completo")  # Agrupa por ID e nome do aluno
        .annotate(contagem=Count("alunos__pk"))         # Conta quantas vezes cada aluno aparece
        .order_by("-contagem")[:3]                      # Ordena pela contagem
    )

    top_modalidades = (
        aulas_relacionadas.filter(professores=professor)
        .values("modalidade__nome")
        .annotate(contagem=Count("modalidade"))
        .order_by("-contagem")[:3]
    )

    aulas_do_professor_paginated = Paginator(aulas_relacionadas.order_by("-data_hora"), 10).get_page(request.GET.get("page"))

    contexto = {
        "professor": professor,
        "titulo": f"Dashboard do Professor: {professor.username}",
        "aulas_do_professor": aulas_do_professor_paginated,
        "data_inicial": data_inicial_str,
        "data_final": data_final_str,
        "total_realizadas": total_realizadas,
        "total_agendadas": total_agendadas,
        "total_canceladas": total_canceladas,
        "total_aluno_ausente": total_aluno_ausente,
        "total_substituido": total_substituido,
        "taxa_presenca": taxa_presenca,
        "top_alunos": top_alunos,
        "top_modalidades": top_modalidades,
    }
    return render(request, "scheduler/professor_detalhe.html", contexto)

# --- NOVA VIEW PARA VERIFICAÇÃO DE CONFLITO VIA AJAX ---
@login_required
def verificar_conflito_aula(request):
    if (
        request.method == "GET"
        and request.headers.get("x-requested-with") == "XMLHttpRequest"
    ):
        professor_id = request.GET.get("professor_id")
        data_hora_str = request.GET.get("data_hora")
        aula_id = request.GET.get("aula_id")  # ID da aula sendo editada (se houver)

        if not professor_id or not data_hora_str:
            return JsonResponse(
                {"conflito": True, "mensagem": "Dados incompletos para verificação."},
                status=400,
            )

        try:
            professor_id = int(professor_id)
            data_hora = datetime.fromisoformat(
                data_hora_str
            )  # Converte a string ISO (YYYY-MM-DDTHH:MM) para datetime
            aula_id = int(aula_id) if aula_id else None  # Converte para int ou None
        except (ValueError, TypeError):
            return JsonResponse(
                {"conflito": True, "mensagem": "Formato de dados inválido."}, status=400
            )

        conflito_info = _check_conflito_aula(professor_id, data_hora, aula_id)
        return JsonResponse(conflito_info)

    return JsonResponse(
        {"conflito": True, "mensagem": "Requisição inválida."}, status=400
    )  # Requisição não-AJAX ou não-GET


def _get_dados_relatorio_agregado(request):
    """
    Função auxiliar que filtra e agrega os dados do relatório.
    """
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")
    professor_filtro_id = request.GET.get("professor_filtro", "")
    modalidade_filtro_id = request.GET.get("modalidade_filtro", "")
    status_filtro = request.GET.get("status_filtro", "")

    aulas_base_queryset = Aula.objects.all()

    # Aplica filtros
    if data_inicial_str:
        try:
            data_inicial = datetime.strptime(data_inicial_str, "%Y-%m-%d").date()
            aulas_base_queryset = aulas_base_queryset.filter(data_hora__date__gte=data_inicial)
        except ValueError: pass
    if data_final_str:
        try:
            data_final = datetime.strptime(data_final_str, "%Y-%m-%d").date()
            aulas_base_queryset = aulas_base_queryset.filter(data_hora__date__lte=data_final)
        except ValueError: pass
    
    # --- CORRIGIDO ---
    if professor_filtro_id:
        aulas_base_queryset = aulas_base_queryset.filter(
            Q(professores__id=professor_filtro_id) | Q(relatorioaula__professor_que_validou__id=professor_filtro_id)
        )
    if modalidade_filtro_id:
        aulas_base_queryset = aulas_base_queryset.filter(modalidade_id=modalidade_filtro_id)
    if status_filtro:
        aulas_base_queryset = aulas_base_queryset.filter(status=status_filtro)

    aulas_por_professor_final = list(aulas_base_queryset.filter(relatorioaula__professor_que_validou__isnull=False).values('relatorioaula__professor_que_validou__username').annotate(aulas_realizadas=Count('id')).order_by('-aulas_realizadas').values('relatorioaula__professor_que_validou__username', 'aulas_realizadas'))
    aulas_por_modalidade_final = list(aulas_base_queryset.values('modalidade__nome', 'modalidade__id').annotate(total_aulas=Count('id'), aulas_realizadas=Count('id', filter=Q(status='Realizada'))).order_by('-total_aulas').values('modalidade__id', 'modalidade__nome', 'total_aulas', 'aulas_realizadas'))

    return {
        "aulas_por_professor": aulas_por_professor_final,
        "aulas_por_modalidade": aulas_por_modalidade_final,
    }

@user_passes_test(is_admin)
def relatorios_aulas(request):
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")
    professor_filtro_id = request.GET.get("professor_filtro", "")
    modalidade_filtro_id = request.GET.get("modalidade_filtro", "")
    status_filtro = request.GET.get("status_filtro", "")
    aluno_filtro_ids = request.GET.getlist("aluno_filtro")

    aulas_base_queryset = Aula.objects.all()

    if data_inicial_str:
        try: data_inicial = datetime.strptime(data_inicial_str, "%Y-%m-%d").date(); aulas_base_queryset = aulas_base_queryset.filter(data_hora__date__gte=data_inicial)
        except ValueError: pass
    if data_final_str:
        try: data_final = datetime.strptime(data_final_str, "%Y-%m-%d").date(); aulas_base_queryset = aulas_base_queryset.filter(data_hora__date__lte=data_final)
        except ValueError: pass
    
    # --- CORRIGIDO ---
    if professor_filtro_id:
        aulas_base_queryset = aulas_base_queryset.filter(
            Q(professores__id=professor_filtro_id) | Q(relatorioaula__professor_que_validou__id=professor_filtro_id)
        )
    if modalidade_filtro_id:
        aulas_base_queryset = aulas_base_queryset.filter(modalidade_id=modalidade_filtro_id)
    
    # --- CORRIGIDO ---
    if status_filtro:
        if status_filtro == 'Substituído':
            aulas_base_queryset = aulas_base_queryset.filter(
                status='Realizada', professores__isnull=False, relatorioaula__professor_que_validou__isnull=False
            ).exclude(professores=F('relatorioaula__professor_que_validou'))
        else:
            aulas_base_queryset = aulas_base_queryset.filter(status=status_filtro)

    if aluno_filtro_ids:
        aluno_filtro_ids = [int(id) for id in aluno_filtro_ids if id.isdigit()]
        if aluno_filtro_ids:
            aulas_base_queryset = aulas_base_queryset.filter(alunos__id__in=aluno_filtro_ids).distinct()


    total_aulas = aulas_base_queryset.count()
    total_realizadas_bruto = aulas_base_queryset.filter(status="Realizada").count()
    total_canceladas = aulas_base_queryset.filter(status="Cancelada").count()
    total_aluno_ausente = aulas_base_queryset.filter(status="Aluno Ausente").count()
    total_agendadas = aulas_base_queryset.filter(status="Agendada").count()
    
    # --- CORRIGIDO ---
    total_substituidas = aulas_base_queryset.filter(
        status='Realizada', professores__isnull=False, relatorioaula__professor_que_validou__isnull=False
    ).exclude(professores__in=F('relatorioaula__professor_que_validou')).count()


    professores = CustomUser.objects.filter(tipo__in=['professor', 'admin'])
    aulas_por_professor_final = professores.annotate(
        total_atribuidas=Count('aulas_lecionadas', distinct=True, filter=Q(aulas_lecionadas__in=aulas_base_queryset)),
        total_realizadas=Count('aulas_validadas_por_mim', distinct=True, filter=Q(aulas_validadas_por_mim__aula__in=aulas_base_queryset))
    ).filter(Q(total_atribuidas__gt=0) | Q(total_realizadas__gt=0)).order_by('-total_realizadas', '-total_atribuidas')

    aulas_por_modalidade_final = list(aulas_base_queryset.filter(modalidade__isnull=False).values('modalidade__id', 'modalidade__nome').annotate(total_aulas=Count('id'), aulas_realizadas=Count('id', filter=Q(status='Realizada'))).order_by('-total_aulas'))

    prof_chart_labels = [prof.username.title() for prof in aulas_por_professor_final]
    prof_chart_data_realizadas = [prof.total_realizadas for prof in aulas_por_professor_final]
    
    professores_list = CustomUser.objects.filter(tipo__in=["professor", "admin"]).order_by("username")
    modalidades_list = Modalidade.objects.all().order_by("nome")
    status_choices = Aula.STATUS_AULA_CHOICES

    contexto = {
        "titulo": "Relatórios de Aulas", "data_inicial": data_inicial_str, "data_final": data_final_str,
        "professor_filtro": professor_filtro_id, "modalidade_filtro": modalidade_filtro_id,
        "status_filtro": status_filtro, "professores_list": professores_list,
        "modalidades_list": modalidades_list, "status_choices": status_choices,
        "total_aulas": total_aulas, "total_agendadas": total_agendadas,
        "total_realizadas": total_realizadas_bruto, "total_canceladas": total_canceladas,
        "total_aluno_ausente": total_aluno_ausente, "total_substituidas": total_substituidas,
        "aulas_por_professor": aulas_por_professor_final, "aulas_por_modalidade": aulas_por_modalidade_final,
        "prof_chart_labels": prof_chart_labels, "prof_chart_data_realizadas": prof_chart_data_realizadas,
        "aluno_filtro_ids": aluno_filtro_ids,
        "alunos_list": Aluno.objects.all().order_by("nome_completo"),
    }
    return render(request, "scheduler/relatorios_aulas.html", contexto)

# --- NOVA VIEW DE EXPORTAÇÃO ---
@user_passes_test(is_admin)
def exportar_relatorio_agregado(request):
    """
    Exporta um relatório gerencial AGREGADO e ESTILIZADO para um arquivo Excel (.xlsx),
    respeitando os filtros aplicados na página de relatórios.
    """
    # 1. Lógica de filtros (AGORA CORRIGIDA E COMPLETA)
    aulas_queryset = Aula.objects.all()
    
    # --- INÍCIO DO BLOCO DE FILTROS CORRIGIDO ---
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")
    professor_filtro_id = request.GET.get("professor_filtro", "")
    modalidade_filtro_id = request.GET.get("modalidade_filtro", "")
    status_filtro = request.GET.get("status_filtro", "")
    aluno_filtro_ids = request.GET.getlist("aluno_filtro")

    if data_inicial_str:
        try: aulas_queryset = aulas_queryset.filter(data_hora__date__gte=datetime.strptime(data_inicial_str, "%Y-%m-%d").date())
        except ValueError: pass
    if data_final_str:
        try: aulas_queryset = aulas_queryset.filter(data_hora__date__lte=datetime.strptime(data_final_str, "%Y-%m-%d").date())
        except ValueError: pass
    if professor_filtro_id:
        aulas_queryset = aulas_queryset.filter(Q(professores__id=professor_filtro_id) | Q(relatorioaula__professor_que_validou__id=professor_filtro_id))
    if modalidade_filtro_id:
        aulas_queryset = aulas_queryset.filter(modalidade_id=modalidade_filtro_id)
    if status_filtro:
        if status_filtro == 'Substituído':
            aulas_queryset = aulas_queryset.filter(status='Realizada', professores__isnull=False, relatorioaula__professor_que_validou__isnull=False).exclude(professores=F('relatorioaula__professor_que_validou'))
        else:
            aulas_queryset = aulas_queryset.filter(status=status_filtro)
    if aluno_filtro_ids:
        aluno_filtro_ids = [int(id) for id in aluno_filtro_ids if id.isdigit()]
        if aluno_filtro_ids:
            aulas_queryset = aulas_queryset.filter(alunos__id__in=aluno_filtro_ids).distinct()
    # --- FIM DO BLOCO DE FILTROS CORRIGIDO ---

    # 2. Cálculo dos KPIs Gerais
    total_aulas = aulas_queryset.count()
    total_realizadas = aulas_queryset.filter(status="Realizada").count()
    total_canceladas = aulas_queryset.filter(status="Cancelada").count()
    total_aluno_ausente = aulas_queryset.filter(status="Aluno Ausente").count()

    # 3. Cálculo dos dados por Professor (Agora sobre o queryset filtrado)
    professores = CustomUser.objects.filter(tipo__in=['professor', 'admin']).annotate(
        total_atribuidas=Count('aulas_lecionadas', distinct=True, filter=Q(aulas_lecionadas__in=aulas_queryset)),
        total_realizadas=Count('aulas_validadas_por_mim', distinct=True, filter=Q(aulas_validadas_por_mim__aula__in=aulas_queryset, aulas_validadas_por_mim__aula__status='Realizada')),
        total_ausencias=Count('aulas_validadas_por_mim', distinct=True, filter=Q(aulas_validadas_por_mim__aula__in=aulas_queryset, aulas_validadas_por_mim__aula__status='Aluno Ausente'))
    ).filter(Q(total_atribuidas__gt=0) | Q(total_realizadas__gt=0)).order_by('-total_realizadas')

    # 4. Cálculo dos dados por Categoria (Agora sobre o queryset filtrado)
    aulas_por_modalidade = aulas_queryset.filter(modalidade__isnull=False).values(
        'modalidade__id', 'modalidade__nome'
    ).annotate(
        total_aulas=Count('id'),
        aulas_realizadas=Count('id', filter=Q(status='Realizada')),
        aulas_ausencias=Count('id', filter=Q(status='Aluno Ausente')),
        aulas_canceladas=Count('id', filter=Q(status='Cancelada'))
    ).order_by('-total_aulas')

    # 5. Criação e Estilização da Planilha Excel
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Relatorio Gerencial"

    # Estilos
    font_bold = Font(bold=True)
    font_header = Font(bold=True, color="FFFFFF")
    fill_header = PatternFill(start_color="2F75B5", end_color="2F75B5", fill_type="solid")
    fill_subheader = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")

    # --- Bloco de KPIs Gerais ---
    ws.merge_cells('B2:E2')
    cell_kpi_header = ws['B2']
    cell_kpi_header.value = "Resumo Geral do Período"
    cell_kpi_header.font = font_header
    cell_kpi_header.fill = fill_header
    cell_kpi_header.alignment = Alignment(horizontal='center')

    ws['B4'] = "Total de Aulas no Período:"; ws['B4'].font = font_bold
    ws['C4'] = total_aulas
    ws['B5'] = "Aulas Realizadas:"; ws['B5'].font = font_bold
    ws['C5'] = total_realizadas
    ws['B6'] = "Aulas com Ausência:"; ws['B6'].font = font_bold
    ws['C6'] = total_aluno_ausente
    ws['B7'] = "Aulas Canceladas:"; ws['B7'].font = font_bold
    ws['C7'] = total_canceladas
    
    # --- Tabela de Resumo por Professor ---
    current_row = 10
    ws.merge_cells(f'B{current_row}:F{current_row}')
    cell_prof_header = ws[f'B{current_row}']
    cell_prof_header.value = "Resumo por Professor"
    cell_prof_header.font = font_header
    cell_prof_header.fill = fill_header
    cell_prof_header.alignment = Alignment(horizontal='center')
    current_row += 1

    prof_headers = ["Professor", "Aulas Atribuídas", "Aulas Realizadas", "Aulas c/ Ausência", "Taxa de Realização (%)"]
    ws.append([''] + prof_headers) # Adiciona uma coluna vazia no início para espaçamento
    for cell in ws[current_row]:
        cell.font = font_bold
        cell.fill = fill_subheader

    current_row += 1
    for p in professores:
        taxa = (p.total_realizadas / p.total_atribuidas * 100) if p.total_atribuidas > 0 else 0
        ws.append(['', p.username.title(), p.total_atribuidas, p.total_realizadas, p.total_ausencias, f"{taxa:.2f}%"])

    # --- Tabela de Resumo por Categoria ---
    current_row += 3 # Espaço entre as tabelas
    ws.merge_cells(f'B{current_row}:G{current_row}')
    cell_cat_header = ws[f'B{current_row}']
    cell_cat_header.value = "Resumo por Categoria"
    cell_cat_header.font = font_header
    cell_cat_header.fill = fill_header
    cell_cat_header.alignment = Alignment(horizontal='center')
    current_row += 1

    cat_headers = ["Categoria", "Total de Aulas", "Aulas Realizadas", "Ausências", "Canceladas", "Taxa de Realização (%)"]
    ws.append([''] + cat_headers)
    for cell in ws[current_row]:
        cell.font = font_bold
        cell.fill = fill_subheader
    
    current_row += 1
    for item in aulas_por_modalidade:
        taxa = (item['aulas_realizadas'] / item['total_aulas'] * 100) if item['total_aulas'] > 0 else 0
        ws.append(['', item['modalidade__nome'].title(), item['total_aulas'], item['aulas_realizadas'], item['aulas_ausencias'], item['aulas_canceladas'], f"{taxa:.2f}%"])
        
    # Ajuste final das colunas
    for i, column_cells in enumerate(ws.columns):
        max_length = 0
        column = get_column_letter(i + 1)
        for cell in column_cells:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    # 6. Preparação da resposta HTTP
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Resumo Gerencial.xlsx"'},
    )
    workbook.save(response)
    
    return response


# --- NOVA VIEW PARA EXPORTAÇÃO DE DADOS ---
@user_passes_test(is_admin)
def exportar_aulas(request):
    """
    Exporta um relatório detalhado de atividades das aulas para um arquivo CSV,
    respeitando os filtros aplicados. Cada linha representa uma atividade.
    """
    # 1. Reaplica a lógica de filtros da página de listagem (nenhuma mudança aqui)
    aulas_queryset = Aula.objects.all()
    # (Toda a sua lógica de filtros por data, professor, aluno, etc., permanece a mesma)
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")
    professor_filtro_id = request.GET.get("professor_filtro", "")
    modalidade_filtro_id = request.GET.get("modalidade_filtro", "")
    status_filtro = request.GET.get("status_filtro", "")
    aluno_filtro_ids = request.GET.getlist("aluno_filtro")

    if data_inicial_str:
        try: aulas_queryset = aulas_queryset.filter(data_hora__date__gte=datetime.strptime(data_inicial_str, "%Y-%m-%d").date())
        except ValueError: pass
    if data_final_str:
        try: aulas_queryset = aulas_queryset.filter(data_hora__date__lte=datetime.strptime(data_final_str, "%Y-%m-%d").date())
        except ValueError: pass
    if professor_filtro_id:
        aulas_queryset = aulas_queryset.filter(Q(professores__id=professor_filtro_id) | Q(relatorioaula__professor_que_validou__id=professor_filtro_id))
    if modalidade_filtro_id:
        aulas_queryset = aulas_queryset.filter(modalidade_id=modalidade_filtro_id)
    if status_filtro:
        if status_filtro == 'Substituído':
            aulas_queryset = aulas_queryset.filter(status='Realizada', professores__isnull=False, relatorioaula__professor_que_validou__isnull=False).exclude(professores=F('relatorioaula__professor_que_validou'))
        else:
            aulas_queryset = aulas_queryset.filter(status=status_filtro)
    if aluno_filtro_ids:
        aluno_filtro_ids = [int(id) for id in aluno_filtro_ids if id.isdigit()]
        if aluno_filtro_ids:
            aulas_queryset = aulas_queryset.filter(alunos__id__in=aluno_filtro_ids).distinct()

    # 2. Otimiza a consulta para performance, buscando todos os dados relacionados de uma vez
    aulas_list = list(aulas_queryset.order_by("data_hora").select_related(
        'modalidade', 'relatorioaula__professor_que_validou'
    ).prefetch_related(
        'alunos', 'professores',
        'relatorioaula__itens_rudimentos',
        'relatorioaula__itens_ritmo',
        'relatorioaula__itens_viradas'
    ))

    # 3. Workbook e Estilos...
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Relatorio Detalhado de Aulas"
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    center_alignment = Alignment(horizontal="center", vertical="center")
    cores_atividades = {
        "Teoria": PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid"),
        "Repertório": PatternFill(start_color="F2DCDB", end_color="F2DCDB", fill_type="solid"),
        "Rudimento": PatternFill(start_color="EAF1DD", end_color="EAF1DD", fill_type="solid"),
        "Ritmo": PatternFill(start_color="DBEEF3", end_color="DBEEF3", fill_type="solid"),
        "Virada": PatternFill(start_color="E5E0EC", end_color="E5E0EC", fill_type="solid"),
        "Observações Gerais": PatternFill(start_color="FDE9D9", end_color="FDE9D9", fill_type="solid"),
        "N/A": PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid"),
    }

    # 4. Cabeçalho
    headers = [
        "ID Aula", "Data e Hora", "Status", "Alunos", "Prof. Atribuído(s)", "Prof. Realizou",
        "Categoria", "Tipo de Conteúdo", "Descrição", "Detalhes (BPM, Livro, Duração)", "Observações do Conteúdo"
    ]
    worksheet.append(headers)
    for col_num, header_title in enumerate(headers, 1):
        cell = worksheet.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment

    # 5. Loop principal com a lógica corrigida
    for i, aula in enumerate(aulas_list):
        if i > 0:
            worksheet.append([])

        alunos_str = ", ".join([al.nome_completo.title() for al in aula.alunos.all()])
        professores_str = ", ".join([p.username.title() for p in aula.professores.all()])
        relatorio = getattr(aula, "relatorioaula", None)
        professor_realizou_str = relatorio.professor_que_validou.username.title() if relatorio and relatorio.professor_que_validou else "N/A"
        data_hora_naive = timezone.localtime(aula.data_hora).replace(tzinfo=None)
        base_row_data = [
            aula.id, data_hora_naive, aula.get_status_display(), alunos_str,
            professores_str, professor_realizou_str, aula.modalidade.nome
        ]

        def adicionar_linha_estilizada(dados_atividade):
            worksheet.append(base_row_data + dados_atividade)
            cor_tipo = dados_atividade[0]
            fill_style = cores_atividades.get(cor_tipo, cores_atividades["N/A"])
            for cell in worksheet[worksheet.max_row]:
                cell.fill = fill_style

        if relatorio:
            conteudo_adicionado = False
            if relatorio.conteudo_teorico:
                adicionar_linha_estilizada(["Teoria", relatorio.conteudo_teorico, "", relatorio.observacoes_teoria or ""])
                conteudo_adicionado = True
            for item in relatorio.itens_rudimentos.all():
                detalhes = f"BPM: {item.bpm or 'N/A'} / Duração: {item.duracao_min or 'N/A'} min"
                adicionar_linha_estilizada(["Rudimento", item.descricao, detalhes, item.observacoes or ""])
                conteudo_adicionado = True
            for item in relatorio.itens_ritmo.all():
                detalhes = f"Livro: {item.livro_metodo or 'N/A'} / BPM: {item.bpm or 'N/A'} / Duração: {item.duracao_min or 'N/A'} min"
                adicionar_linha_estilizada(["Ritmo", item.descricao, detalhes, item.observacoes or ""])
                conteudo_adicionado = True
            for item in relatorio.itens_viradas.all():
                detalhes = f"BPM: {item.bpm or 'N/A'} / Duração: {item.duracao_min or 'N/A'} min"
                adicionar_linha_estilizada(["Virada", item.descricao, detalhes, item.observacoes or ""])
                conteudo_adicionado = True
            if relatorio.repertorio_musicas:
                adicionar_linha_estilizada(["Repertório", relatorio.repertorio_musicas, "", relatorio.observacoes_repertorio or ""])
                conteudo_adicionado = True
            if relatorio.observacoes_gerais:
                adicionar_linha_estilizada(["Observações Gerais", relatorio.observacoes_gerais, "", ""])
                conteudo_adicionado = True
            if not conteudo_adicionado:
                adicionar_linha_estilizada(["N/A", "Relatório existe, mas está vazio.", "", ""])
        else:
            adicionar_linha_estilizada(["N/A", "Aula sem relatório criado.", "", ""])
    
    # 7. Ajuste de colunas
    for col_num, _ in enumerate(headers, 1):
        column_letter = get_column_letter(col_num)
        worksheet.column_dimensions[column_letter].width = 20
    worksheet.column_dimensions['D'].width = 40
    worksheet.column_dimensions['I'].width = 40
    worksheet.column_dimensions['J'].width = 50
    worksheet.column_dimensions['K'].width = 50
    
    # 8. Retorno da resposta
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Relatório de Aulas.xlsx"'},
    )
    workbook.save(response)
    return response



@login_required
def get_horarios_ocupados(request):
    professor_id = request.GET.get("professor_id")
    data_selecionada_str = request.GET.get(
        "data"
    )  # Data selecionada no calendário (YYYY-MM-DD)
    aula_id = request.GET.get("aula_id")  # ID da aula atual sendo editada (se houver)

    horarios_ocupados = (
        []
    )  # Lista de strings de horários (HH:MM) para o dia selecionado
    dias_com_aulas = []  # Lista de strings de datas (YYYY-MM-DD) para o professor

    if professor_id:  # A busca por dias com aulas não precisa de uma data específica
        try:
            professor_id = int(professor_id)
            aula_id = int(aula_id) if aula_id else None

            # --- Buscar todos os dias com aulas para o professor selecionado ---
            # Filtra aulas para o professor
            aulas_do_professor = (
                Aula.objects.filter(professor_id=professor_id)
                .values_list("data_hora__date", flat=True)
                .distinct()
            )  # Pega apenas as datas únicas

            if aula_id:  # Exclui a própria aula se estiver editando
                aulas_do_professor = aulas_do_professor.exclude(id=aula_id)

            for data_aula in aulas_do_professor:
                dias_com_aulas.append(data_aula.strftime("%Y-%m-%d"))

            # --- Buscar horários ocupados para o dia específico (se fornecido) ---
            if data_selecionada_str:
                data_selecionada = datetime.strptime(
                    data_selecionada_str, "%Y-%m-%d"
                ).date()

                aulas_do_dia = Aula.objects.filter(
                    professor_id=professor_id, data_hora__date=data_selecionada
                )
                if aula_id:  # Exclui a própria aula se estiver editando
                    aulas_do_dia = aulas_do_dia.exclude(id=aula_id)

                for aula in aulas_do_dia:
                    horarios_ocupados.append(aula.data_hora.strftime("%H:%M"))

            return JsonResponse(
                {
                    "horarios_ocupados": horarios_ocupados,
                    "dias_com_aulas": dias_com_aulas,
                }
            )

        except (ValueError, TypeError) as e:
            return JsonResponse(
                {
                    "horarios_ocupados": [],
                    "dias_com_aulas": [],
                    "erro": f"Dados inválidos: {e}",
                },
                status=400,
            )

    return JsonResponse(
        {
            "horarios_ocupados": [],
            "dias_com_aulas": [],
            "erro": "Professor não fornecido.",
        },
        status=400,
    )


#  --- NOVA VIEW PARA OBTER EVENTOS DO CALENDÁRIO (FULLCALENDAR) ---
@login_required
def get_eventos_calendario(request):
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")
    professor_filtro_id = request.GET.get("professor_filtro_id", "")

    events = []

    if not (start_str and end_str):
        return JsonResponse({"error": "Período não fornecido."}, status=400)

    try:
        start_date = datetime.fromisoformat(start_str.replace("Z", "+00:00")).date()
        end_date = datetime.fromisoformat(end_str.replace("Z", "+00:00")).date()

        aulas_no_periodo = Aula.objects.filter(data_hora__date__range=(start_date, end_date))

        # Filtro por professor
        if request.user.tipo == "professor":
            aulas_no_periodo = aulas_no_periodo.filter(professores=request.user)
        elif request.user.tipo == "admin" and professor_filtro_id:
            aulas_no_periodo = aulas_no_periodo.filter(professores__id=professor_filtro_id)
        
        # --- OTIMIZAÇÃO E CORREÇÃO PRINCIPAL ---
        # Usamos prefetch_related para buscar todos os alunos e professores de uma vez,
        # evitando múltiplas queries ao banco de dados e melhorando a performance.
        aulas_no_periodo = aulas_no_periodo.select_related(
            "modalidade", "relatorioaula", "relatorioaula__professor_que_validou"
        ).prefetch_related(
            'alunos', 'professores'
        ).distinct()


        for aula in aulas_no_periodo:
            # --- NOVA LÓGICA PARA LIDAR COM MÚLTIPLOS ALUNOS/PROFESSORES ---
            alunos_list = list(aula.alunos.all())
            professores_list = list(aula.professores.all())

            title = ""
            aluno_prop_str = ""
            
            # Define o título do evento e a string de alunos para o popover
            if len(alunos_list) == 1:
                # Se há apenas um aluno, o título é o nome dele
                title = f"{alunos_list[0].nome_completo.split()[0].title()} ({aula.modalidade.nome})"
                aluno_prop_str = alunos_list[0].nome_completo
            elif len(alunos_list) > 1:
                # Se for em grupo, o título é genérico
                title = f"Grupo: {aula.modalidade.nome}"
                aluno_prop_str = f"{len(alunos_list)} alunos"
            else:
                # Se não houver alunos (Ex: Atividade Complementar)
                title = aula.modalidade.nome
                aluno_prop_str = "Nenhum aluno"

            # Junta os nomes dos professores para o popover
            prof_atribuido_str = ", ".join([p.username.title() for p in professores_list]) or "N/A"
            
            event_class = f'status-{aula.status.replace(" ", "")}'
            professor_realizou = getattr(aula, 'relatorioaula', None) and getattr(aula.relatorioaula, 'professor_que_validou', None)
            
            events.append({
                "title": title,
                "start": aula.data_hora.isoformat(),
                "url": f"/aula/{aula.pk}/validar/", # A URL pode ser a de validar/ver relatório
                "classNames": [event_class],
                "extendedProps": {
                    "status": aula.status,
                    "aluno": aluno_prop_str,
                    "professor_atribuido": prof_atribuido_str,
                    "professor_realizou": professor_realizou.username.title() if professor_realizou else "N/A",
                    "modalidade": aula.modalidade.nome.title(),
                },
            })

        return JsonResponse(events, safe=False)

    except (ValueError, TypeError) as e:
        # Em caso de erro, é útil registrar o erro no console do servidor para depuração
        print(f"Erro em get_eventos_calendario: {e}")
        return JsonResponse({"error": "Erro interno ao processar a requisição."}, status=500)


@login_required
def perfil_usuario(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Seu perfil foi atualizado com sucesso!')
            return redirect('scheduler:perfil_usuario') # Redireciona de volta para a página de perfil
        else:
            messages.error(request, 'Erro ao atualizar seu perfil. Verifique os dados.')
    else:
        form = UserProfileForm(instance=user) # Preenche o formulário com os dados do usuário
    
    contexto = {
        'form': form,
        'user_obj': user, # Passa o objeto usuário para o template (útil para exibir a foto/iniciais)
        'titulo': 'Meu Perfil'
    }
    return render(request, 'scheduler/perfil_usuario.html', contexto)
