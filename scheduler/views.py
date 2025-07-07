from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Aula, Aluno, RelatorioAula, Modalidade, CustomUser
# --- IMPORTS ATUALIZADOS ---
from .forms import (
    AlunoForm,
    AulaForm,
    ModalidadeForm,
    ProfessorForm,
    RelatorioAulaForm,      # O formulário principal, agora menor
    ItemRudimentoFormSet,   # O novo formset de rudimentos
    ItemRitmoFormSet,       # O novo formset de ritmo
    ItemViradaFormSet       # O novo formset de viradas
)
from django.contrib import messages
import calendar
from datetime import datetime
from django.utils import timezone
from django.db.models import Count, Min, Case, When, Q, OuterRef, Subquery, F
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
import csv


# --- Funções de Teste para Permissões ---
def is_admin(user):
    return user.is_authenticated and user.tipo == "admin"


# --- Função auxiliar para verificar conflitos (NÃO É UMA VIEW) ---
def _check_conflito_aula(professor_id, data_hora, aula_id=None):
    """
    Verifica se um professor já tem uma aula agendada para o mesmo horário.
    Args:
        professor_id (int): O ID do professor.
        data_hora (datetime object): A data e hora da aula a ser verificada.
        aula_id (int, optional): O ID da aula atual sendo editada. Se fornecido,
                                 essa aula será excluída da verificação de conflito.
                                 Defaults to None.
    Returns:
        dict: {'conflito': bool, 'mensagem': str}
    """

    aulas_conflitantes = Aula.objects.filter(
        professor_id=professor_id, data_hora=data_hora
    )

    if aula_id: 
        aulas_conflitantes = aulas_conflitantes.exclude(id=aula_id)

    if aulas_conflitantes.exists():
        aula_existente = aulas_conflitantes.first()
        return {
            "conflito": True,
            "mensagem": f"Conflito! Professor já tem aula com {aula_existente.aluno.nome_completo} em {aula_existente.data_hora.strftime('%H:%M')}.",
        }
    return {"conflito": False, "mensagem": "Horário disponível."}


# --- Views Principais (dashboard) ---
@login_required
def dashboard(request):
    now = timezone.now()
    today = now.date()
    next_week = today + timezone.timedelta(days=7)
    
    # --- LÓGICA PARA O DASHBOARD DO ADMIN ---
    if request.user.tipo == 'admin':
        # KPIs do Admin
        # Query base para as aulas relevantes de hoje (não canceladas)
        aulas_do_dia_queryset = Aula.objects.filter(data_hora__date=today).exclude(status__in=['Cancelada', 'Aluno Ausente'])

        # A contagem do KPI agora reflete a mesma lógica
        aulas_hoje_count = aulas_do_dia_queryset.count()
        aulas_semana_count = Aula.objects.filter(data_hora__date__range=[today, next_week]).count()
        aulas_agendadas_total = Aula.objects.filter(status='Agendada', data_hora__gte=now).count()

        # Listas para o Admin
        aulas_do_dia = Aula.objects.filter(data_hora__date=today).order_by('data_hora')
        aulas_da_semana = Aula.objects.filter(data_hora__date__range=[today, next_week]).order_by('data_hora')
        
        # Lista de professores para o filtro do calendário
        professores_list = CustomUser.objects.filter(tipo__in=["professor", "admin"]).order_by("username")
        
        contexto = {
            "titulo": "Dashboard do Administrador",
            "today": today,
            "aulas_hoje_count": aulas_hoje_count,
            "aulas_semana_count": aulas_semana_count,
            "aulas_agendadas_total": aulas_agendadas_total,
            "aulas_do_dia": aulas_do_dia,
            "aulas_da_semana": aulas_da_semana,
            "professores_list": professores_list,
        }
    
    # --- LÓGICA PARA O DASHBOARD DO PROFESSOR ---
    else: # Se não é admin, é professor
        # Queryset base com todas as aulas do professor
        aulas_do_professor = Aula.objects.filter(
            Q(professor=request.user) | Q(relatorioaula__professor_que_validou=request.user)
        ).distinct()

        # KPIs do Professor
        aulas_hoje_count = aulas_do_professor.filter(data_hora__date=today).count()
        aulas_semana_count = aulas_do_professor.filter(data_hora__date__range=[today, next_week]).count()
        
        # Aulas que já aconteceram mas ainda estão "Agendadas", ou seja, pendentes de relatório
        aulas_pendentes_count = aulas_do_professor.filter(status='Agendada', data_hora__lt=now).count()

        # Listas para o Professor
        aulas_do_dia = aulas_do_professor.filter(data_hora__date=today).order_by('data_hora')
        proximas_aulas_semana = aulas_do_professor.filter(status='Agendada', data_hora__gte=now, data_hora__date__lte=next_week).order_by('data_hora')
        aulas_pendentes_validacao = aulas_do_professor.filter(status='Agendada', data_hora__lt=now).order_by('data_hora')

        contexto = {
            "titulo": "Meu Dashboard",
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
    if request.method == "POST":
        form = AulaForm(request.POST)
        if form.is_valid():
            aluno = form.cleaned_data["aluno"]
            professor = form.cleaned_data["professor"]
            modalidade = form.cleaned_data["modalidade"]
            data_hora_inicial = form.cleaned_data["data_hora"]
            status = form.cleaned_data["status"]
            recorrente_mensal = form.cleaned_data.get("recorrente_mensal", False)

            aula_id = form.instance.pk

            if recorrente_mensal:
                ano = data_hora_inicial.year
                mes = data_hora_inicial.month
                dia_da_semana = data_hora_inicial.weekday()

                num_dias = calendar.monthrange(ano, mes)[1]
                datas_do_mes = [
                    data_hora_inicial.replace(day=d) for d in range(1, num_dias + 1)
                ]

                datas_recorrentes = [
                    d
                    for d in datas_do_mes
                    if d.weekday() == dia_da_semana and d.day >= data_hora_inicial.day
                ]

                aulas_criadas_count = 0
                aulas_conflito_count = 0

                for data_recorrente in datas_recorrentes:
                    data_hora_recorrente = data_recorrente.replace(
                        hour=data_hora_inicial.hour,
                        minute=data_hora_inicial.minute,
                        second=data_hora_inicial.second,
                        microsecond=data_hora_inicial.microsecond,
                    )

                    conflito_info = _check_conflito_aula(
                        professor.id, data_hora_recorrente, aula_id
                    )

                    if not conflito_info["conflito"]:
                        Aula.objects.create(
                            aluno=aluno,
                            professor=professor,
                            modalidade=modalidade,
                            data_hora=data_hora_recorrente,
                            status=status,
                        )
                        aulas_criadas_count += 1
                    else:
                        aulas_conflito_count += 1
                        messages.warning(
                            request,
                            f"Conflito de agendamento em {data_hora_recorrente.strftime('%d/%m/%Y %H:%M')}: {conflito_info['mensagem']}",
                        )

                if aulas_criadas_count > 0:
                    messages.success(
                        request,
                        f"{aulas_criadas_count} aulas recorrentes agendadas com sucesso!",
                    )
                if aulas_conflito_count > 0:
                    messages.info(
                        request,
                        f"{aulas_conflito_count} aulas não puderam ser agendadas devido a conflitos.",
                    )

                return redirect("scheduler:dashboard")

            else:  # Comportamento padrão para aula única
                conflito_info = _check_conflito_aula(
                    professor.id, data_hora_inicial, aula_id
                )

                if not conflito_info["conflito"]:
                    Aula.objects.create(
                        aluno=aluno,
                        professor=professor,
                        modalidade=modalidade,
                        data_hora=data_hora_inicial,
                        status=status,
                    )
                    messages.success(request, "Aula agendada com sucesso!")
                    return redirect("scheduler:dashboard")
                else:
                    messages.error(request, conflito_info["mensagem"])
                    # Para re-renderizar o formulário com dados e dropdowns, passamos os objetos
                    alunos = Aluno.objects.all().order_by("nome_completo")
                    professores = CustomUser.objects.filter(tipo="professor").order_by(
                        "username"
                    )
                    modalidades = Modalidade.objects.all().order_by("nome")

                    contexto = {
                        "form": form,
                        "titulo": "Agendar Nova Aula",
                        "alunos_list": alunos,  # NOVO: para popular o select de alunos
                        "professores_list": professores,  # NOVO: para popular o select de professores
                        "modalidades_list": modalities,  # NOVO: para popular o select de modalidades
                    }
                    return render(request, "scheduler/aula_form.html", contexto)

    else:  # GET request
        form = AulaForm()
        # Para GET request, preenchemos as listas para os dropdowns
        alunos = Aluno.objects.all().order_by("nome_completo")
        professores = CustomUser.objects.filter(tipo="professor").order_by("username")
        modalidades = Modalidade.objects.all().order_by("nome")

        contexto = {
            "form": form,
            "titulo": "Agendar Nova Aula",
            "alunos_list": alunos,  # NOVO
            "professores_list": professores,  # NOVO
            "modalidades_list": modalidades,  # NOVO
        }
        return render(request, "scheduler/aula_form.html", contexto)


@user_passes_test(is_admin)
def editar_aula(request, pk):
    aula = get_object_or_404(Aula, pk=pk)
    if request.method == "POST":
        form = AulaForm(request.POST, instance=aula)
        form.fields.pop("recorrente_mensal", None)

        if form.is_valid():
            professor = form.cleaned_data["professor"]
            data_hora = form.cleaned_data["data_hora"]

            conflito_info = _check_conflito_aula(professor.id, data_hora, aula.pk)

            if not conflito_info["conflito"]:
                form.save()
                messages.success(request, "Aula atualizada com sucesso!")
                return redirect("scheduler:dashboard")
            else:
                messages.error(request, conflito_info["mensagem"])
                # Para re-renderizar o formulário com dados e dropdowns, passamos os objetos
                alunos = Aluno.objects.all().order_by("nome_completo")
                professores = CustomUser.objects.filter(tipo="professor").order_by(
                    "username"
                )
                modalidades = Modalidade.objects.all().order_by("nome")

                contexto = {
                    "form": form,
                    "titulo": f"Editar Aula de: {aula.aluno}",
                    "alunos_list": alunos,  # NOVO
                    "professores_list": professores,  # NOVO
                    "modalidades_list": modalidades,  # NOVO
                }
                return render(request, "scheduler/aula_form.html", contexto)
    else:  # GET request
        form = AulaForm(instance=aula)
        form.fields.pop("recorrente_mensal", None)

        # Para GET request, preenchemos as listas para os dropdowns
        alunos = Aluno.objects.all().order_by("nome_completo")
        professores = CustomUser.objects.filter(tipo="professor").order_by("username")
        modalidades = Modalidade.objects.all().order_by("nome")

        contexto = {
            "form": form,
            "titulo": f"Editar Aula de: {aula.aluno}",
            "alunos_list": alunos,  # NOVO
            "professores_list": professores,  # NOVO
            "modalidades_list": modalidades,  # NOVO
        }
        return render(request, "scheduler/aula_form.html", contexto)


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

    # Busca aulas futuras, com status 'Agendada', e que NÃO SÃO do professor logado
    aulas_disponiveis = Aula.objects.filter(
        data_hora__gte=now,
        status='Agendada'
    ).exclude(
        professor=request.user
    ).order_by('data_hora')

    # Paginação para a lista
    paginator = Paginator(aulas_disponiveis, 10)
    page_number = request.GET.get('page')
    aulas = paginator.get_page(page_number)

    contexto = {
        'titulo': 'Aulas Disponíveis para Substituição',
        'aulas': aulas,
    }
    return render(request, 'scheduler/aulas_para_substituir.html', contexto)


# --- VIEWS DE GERENCIAMENTO DE ALUNOS ---
@login_required
def listar_alunos(request):
    # --- NOVO: Lógica de Busca ---
    search_query = request.GET.get("q", "")

    # Define a data/hora atual para encontrar a "próxima" aula
    now = timezone.now()

    # Queryset base anotado para incluir dados extras
    alunos_queryset = Aluno.objects.annotate(
        # Conta o total de aulas associadas a cada aluno
        total_aulas=Count('aula'),
        # Encontra a data mínima (mais próxima) de uma aula que ainda vai acontecer
        proxima_aula=Min(
            Case(
                When(aula__data_hora__gte=now, then='aula__data_hora'),
                default=None
            )
        )
    )

    # Aplica o filtro de busca se houver um termo
    if search_query:
        alunos_queryset = alunos_queryset.filter(
            Q(nome_completo__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(telefone__icontains=search_query)
        )
    
    # Ordena o resultado final pelo nome do aluno
    alunos = alunos_queryset.order_by("nome_completo")

    contexto = {
        "alunos": alunos,
        "titulo": "Gerenciamento de Alunos",
        "search_query": search_query, # Passa o termo de busca para o template
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
    
    # Queryset base com todas as aulas do aluno
    aulas_do_aluno = Aula.objects.filter(aluno=aluno)

    # --- INÍCIO DA COLETA DE DADOS PARA O DASHBOARD DO ALUNO ---
    
    # 1. KPIs de Status
    total_aulas = aulas_do_aluno.count()
    total_realizadas = aulas_do_aluno.filter(status="Realizada").count()
    total_canceladas = aulas_do_aluno.filter(status="Cancelada").count()
    total_aluno_ausente = aulas_do_aluno.filter(status="Aluno Ausente").count()
    total_agendadas = aulas_do_aluno.filter(status="Agendada").count()

    # 2. Cálculo da Taxa de Presença
    aulas_contabilizaveis_presenca = total_realizadas + total_aluno_ausente
    taxa_presenca = 0
    if aulas_contabilizaveis_presenca > 0:
        taxa_presenca = (total_realizadas / aulas_contabilizaveis_presenca) * 100

    # 3. Top Professores e Modalidades (filtrando apenas aulas com professor)
    top_professores = (
        aulas_do_aluno.filter(professor__isnull=False)
        .values("professor__username")
        .annotate(contagem=Count("professor"))
        .order_by("-contagem")[:3]
    )

    top_modalidades = (
        aulas_do_aluno.values("modalidade__nome")
        .annotate(contagem=Count("modalidade"))
        .order_by("-contagem")[:3]
    )

    # --- FIM DA COLETA DE DADOS ---

    # Paginação para a tabela de histórico (seu código existente)
    paginator = Paginator(aulas_do_aluno.order_by("-data_hora"), 5) # Ordena o queryset para paginação
    page = request.GET.get("page")
    try:
        aulas_do_aluno_paginated = paginator.page(page)
    except PageNotAnInteger:
        aulas_do_aluno_paginated = paginator.page(1)
    except EmptyPage:
        aulas_do_aluno_paginated = paginator.page(paginator.num_pages)

    # Contexto final com todos os novos dados
    contexto = {
        "aluno": aluno,
        "aulas_do_aluno": aulas_do_aluno_paginated,
        "titulo": f"Perfil do Aluno: {aluno.nome_completo}",
        
        # Novos KPIs para o dashboard
        "total_aulas": total_aulas,
        "total_realizadas": total_realizadas,
        "total_canceladas": total_canceladas,
        "total_aluno_ausente": total_aluno_ausente,
        "total_agendadas": total_agendadas,
        "taxa_presenca": taxa_presenca,

        # Novas Listas
        "top_professores": top_professores,
        "top_modalidades": top_modalidades,
    }
    return render(request, "scheduler/aluno_detalhe.html", contexto)


@login_required
def listar_aulas(request):
    # 1. Obtenção de todos os parâmetros de filtro e ordenação da URL
    order_by = request.GET.get("order_by", "data_hora")
    direction = request.GET.get("direction", "asc")
    search_query = request.GET.get("q", "")
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")
    professor_filtro_id = request.GET.get("professor_filtro", "")
    modalidade_filtro_id = request.GET.get("modalidade_filtro", "")
    status_filtro = request.GET.get("status_filtro", "")

    # 2. Definição do queryset base, diferenciando Admin de Professor
    if request.user.tipo == "admin":
        aulas_queryset = Aula.objects.all()
        contexto_titulo = "Histórico Geral de Aulas"
    else:  # Professor
        aulas_queryset = Aula.objects.filter(
            Q(professor=request.user) | Q(relatorioaula__professor_que_validou=request.user)
        ).distinct()
        contexto_titulo = "Meu Histórico de Aulas"

    # 3. Aplicação de todos os filtros ao queryset base
    if search_query:
        aulas_queryset = aulas_queryset.filter(
            Q(aluno__nome_completo__icontains=search_query) |
            Q(professor__username__icontains=search_query) |
            Q(modalidade__nome__icontains=search_query) |
            Q(relatorioaula__professor_que_validou__username__icontains=search_query)
        )
    if data_inicial_str:
        try:
            data_inicial = datetime.strptime(data_inicial_str, "%Y-%m-%d").date()
            aulas_queryset = aulas_queryset.filter(data_hora__date__gte=data_inicial)
        except ValueError:
            messages.error(request, "Formato de Data Inicial inválido. Use AAAA-MM-DD.")
    if data_final_str:
        try:
            data_final = datetime.strptime(data_final_str, "%Y-%m-%d").date()
            aulas_queryset = aulas_queryset.filter(data_hora__date__lte=data_final)
        except ValueError:
            messages.error(request, "Formato de Data Final inválido. Use AAAA-MM-DD.")
    if professor_filtro_id:
        aulas_queryset = aulas_queryset.filter(Q(professor_id=professor_filtro_id) | Q(relatorioaula__professor_que_validou_id=professor_filtro_id))
    if modalidade_filtro_id:
        aulas_queryset = aulas_queryset.filter(modalidade_id=modalidade_filtro_id)
    if status_filtro:
        if status_filtro == 'Substituído':
            aulas_queryset = aulas_queryset.filter(
                status='Realizada', professor__isnull=False, relatorioaula__professor_que_validou__isnull=False
            ).exclude(professor=F('relatorioaula__professor_que_validou'))
        else:
            aulas_queryset = aulas_queryset.filter(status=status_filtro)

    # 4. Cálculo dos KPIs para os cards de resumo (APÓS todos os filtros serem aplicados)
    aulas_kanban = {
        'agendada': aulas_queryset.filter(status='Agendada').order_by('data_hora'),
        'realizada': aulas_queryset.filter(status='Realizada').order_by('-data_hora')[:10], # Limita para as 10 últimas
        'cancelada': aulas_queryset.filter(status='Cancelada').order_by('-data_hora')[:10],
        'aluno_ausente': aulas_queryset.filter(status='Aluno Ausente').order_by('-data_hora')[:10],
    }

    # 5. Aplicação da ordenação
    valid_order_fields = {
        "aluno": "aluno__nome_completo",
        "modalidade": "modalidade__nome",
        "professor_atribuido": "professor__username",
        "professor_realizou": "relatorioaula__professor_que_validou__username",
        "data_hora": "data_hora",
        "status": "status",
    }
    order_field = valid_order_fields.get(order_by, "data_hora")
    if direction == "desc":
        order_field = f"-{order_field}"
    
    aulas_queryset = aulas_queryset.order_by(order_field)

    # 6. Paginação do resultado final
    paginator = Paginator(aulas_queryset, 10)
    page_number = request.GET.get("page")
    aulas = paginator.get_page(page_number)

    # 7. Preparação de dados para popular os dropdowns de filtro no template
    professores_list = CustomUser.objects.filter(tipo__in=["professor", "admin"]).order_by("username")
    modalidades_list = Modalidade.objects.all().order_by("nome")
    status_choices = Aula.STATUS_AULA_CHOICES

    # 8. Montagem final do contexto que será enviado para o template
    contexto = {
        "aulas": aulas,
        "titulo": contexto_titulo,
        "order_by": order_by,
        "direction": direction,
        
        # Valores dos filtros para preencher o formulário
        "search_query": search_query,
        "data_inicial": data_inicial_str,
        "data_final": data_final_str,
        "professor_filtro": professor_filtro_id,
        "modalidade_filtro": modalidade_filtro_id,
        "status_filtro": status_filtro,
        
        # Listas para popular os dropdowns
        "professores_list": professores_list,
        "modalidades_list": modalidades_list,
        "status_choices": status_choices,

        "aulas_kanban": aulas_kanban,
    }

    return render(request, "scheduler/aula_listar.html", contexto)


@login_required
@user_passes_test(lambda u: u.tipo in ['admin', 'professor'])
def validar_aula(request, pk):
    aula = get_object_or_404(Aula, pk=pk)
    # get_or_create continua sendo a abordagem correta para o objeto pai.
    relatorio, created = RelatorioAula.objects.get_or_create(aula=aula)

    # Lógica de modo de visualização/edição (permanece a mesma)
    url_mode = request.GET.get('mode')
    if aula.status == "Agendada":
        view_mode = "editar"
    elif url_mode in ["visualizar", "editar"]:
        view_mode = url_mode
    else:
        view_mode = "visualizar"

    # Se a requisição for POST (usuário está salvando o formulário)
    if request.method == 'POST':
        # 1. Instancie o formulário principal E todos os formsets com os dados do POST.
        #    O 'instance=relatorio' conecta os formsets ao relatório correto.
        #    O 'prefix' é crucial para o Django diferenciar os dados de cada formset.
        form = RelatorioAulaForm(request.POST, instance=relatorio)
        rudimentos_formset = ItemRudimentoFormSet(request.POST, instance=relatorio, prefix='rudimentos')
        ritmo_formset = ItemRitmoFormSet(request.POST, instance=relatorio, prefix='ritmo')
        viradas_formset = ItemViradaFormSet(request.POST, instance=relatorio, prefix='viradas')

        # 2. Verifique se o formulário principal E TODOS os formsets são válidos.
        if form.is_valid() and rudimentos_formset.is_valid() and ritmo_formset.is_valid() and viradas_formset.is_valid():
            
            # Salva o formulário principal (commit=False para adicionar o professor antes)
            relatorio_salvo = form.save(commit=False)
            relatorio_salvo.professor_que_validou = request.user
            relatorio_salvo.save() # Agora salva o relatório no banco.

            # 3. Salva os formsets. O Django magicamente cria, atualiza ou deleta
            #    os itens (ItemRudimento, etc.) conforme a interação do usuário.
            rudimentos_formset.save()
            ritmo_formset.save()
            viradas_formset.save()
            
            # Atualiza o status da aula e salva
            aula.status = 'Realizada'
            aula.save()

            messages.success(request, 'Relatório da aula salvo e aula marcada como Realizada!')
            return redirect('scheduler:aula_listar')
        else:
            # Se qualquer um dos formulários ou formsets for inválido, exibe um erro.
            # O Django automaticamente re-renderizará os formulários com os erros.
            messages.error(request, 'Erro ao salvar o relatório. Verifique os campos marcados.')
    
    # Se a requisição for GET (usuário está abrindo a página pela primeira vez)
    else:
        # Apenas instancie o formulário e os formsets vazios ou com dados existentes.
        form = RelatorioAulaForm(instance=relatorio)
        rudimentos_formset = ItemRudimentoFormSet(instance=relatorio, prefix='rudimentos')
        ritmo_formset = ItemRitmoFormSet(instance=relatorio, prefix='ritmo')
        viradas_formset = ItemViradaFormSet(instance=relatorio, prefix='viradas')

    # 4. Passe todos os formulários e formsets para o contexto do template.
    context = {
        'aula': aula,
        'relatorio': relatorio,
        'form': form, # Formulário principal
        'rudimentos_formset': rudimentos_formset, # Formset de rudimentos
        'ritmo_formset': ritmo_formset,           # Formset de ritmo
        'viradas_formset': viradas_formset,       # Formset de viradas
        'view_mode': view_mode,
    }
    return render(request, 'scheduler/aula_validar.html', context)

# --- VIEWS PARA GERENCIAMENTO DE MODALIDADES ---


@user_passes_test(is_admin)
def listar_modalidades(request):
    # Lógica de Busca
    search_query = request.GET.get("q", "")
    now = timezone.now()

    # Queryset base
    modalidades_queryset = Modalidade.objects.all()

    # --- ANOTAÇÕES PARA DADOS EXTRAS ---
    modalidades_queryset = modalidades_queryset.annotate(
        # Conta o total de aulas para cada modalidade
        total_aulas=Count('aula'),
        
        # Conta quantos alunos únicos têm aulas futuras agendadas nesta modalidade
        alunos_ativos=Count(
            'aula__aluno', 
            distinct=True, 
            filter=Q(aula__data_hora__gte=now)
        ),

        # Encontra a data da próxima aula agendada para esta modalidade
        proxima_aula=Min(
            Case(
                When(aula__data_hora__gte=now, then='aula__data_hora'),
                default=None
            )
        )
    )

    # Aplica o filtro de busca
    if search_query:
        modalidades_queryset = modalidades_queryset.filter(nome__icontains=search_query)
    
    # Ordena pelo nome da modalidade
    modalidades = modalidades_queryset.order_by("nome")

    contexto = {
        "modalidades": modalidades,
        "titulo": "Gerenciamento de Modalidades",
        "search_query": search_query,
    }
    return render(request, "scheduler/modalidade_listar.html", contexto)



@user_passes_test(is_admin)
def criar_modalidade(request):
    if request.method == "POST":
        form = ModalidadeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Modalidade criada com sucesso!")
            return redirect("scheduler:modalidade_listar")
    else:
        form = ModalidadeForm()
    contexto = {"form": form, "titulo": "Adicionar Nova Modalidade"}
    return render(request, "scheduler/modalidade_form.html", contexto)


@user_passes_test(is_admin)
def editar_modalidade(request, pk):
    modalidade = get_object_or_404(Modalidade, pk=pk)
    if request.method == "POST":
        form = ModalidadeForm(request.POST, instance=modalidade)
        if form.is_valid():
            form.save()
            messages.success(request, "Modalidade atualizada com sucesso!")
            return redirect("scheduler:modalidade_listar")
    else:
        form = ModalidadeForm(instance=modalidade)
    contexto = {"form": form, "titulo": f"Editar Modalidade: {modalidade.nome}"}
    return render(request, "scheduler/modalidade_form.html", contexto)


@user_passes_test(is_admin)
def excluir_modalidade(request, pk):
    modalidade = get_object_or_404(Modalidade, pk=pk)
    if modalidade.aula_set.exists():
        messages.error(
            request,
            f'Não é possível excluir a modalidade "{modalidade.nome}" porque há aulas associadas a ela. Remova as aulas primeiro.',
        )
        return redirect("scheduler:modalidade_listar")

    if request.method == "POST":
        modalidade.delete()
        messages.success(request, "Modalidade excluída com sucesso!")
        return redirect("scheduler:modalidade_listar")
    contexto = {
        "modalidade": modalidade,
        "titulo": f"Confirmar Exclusão de Modalidade: {modalidade.nome}",
    }
    return render(request, "scheduler/modalidade_confirm_delete.html", contexto)


@user_passes_test(is_admin) # Apenas admins podem ver os detalhes da modalidade
def detalhe_modalidade(request, pk):
    modalidade = get_object_or_404(Modalidade, pk=pk)
    
    # Queryset base para todas as aulas desta modalidade
    aulas_da_modalidade = Aula.objects.filter(modalidade=modalidade)
    now = timezone.now()

    # --- COLETA DE DADOS PARA OS KPIs ---
    
    # 1. KPIs de Contagem
    total_aulas = aulas_da_modalidade.count()
    total_realizadas = aulas_da_modalidade.filter(status="Realizada").count()
    
    # Alunos ativos são alunos únicos com aulas futuras agendadas nesta modalidade
    alunos_ativos_count = aulas_da_modalidade.filter(
        data_hora__gte=now
    ).values('aluno').distinct().count()

    # Professores que lecionam esta modalidade (professores únicos)
    professores_count = aulas_da_modalidade.filter(
        professor__isnull=False
    ).values('professor').distinct().count()

    # --- DADOS PARA O GRÁFICO DE ATIVIDADE MENSAL ---
    aulas_por_mes = aulas_da_modalidade.annotate(
        mes=TruncMonth('data_hora') # Agrupa as aulas pelo primeiro dia do mês
    ).values('mes').annotate(
        contagem=Count('id') # Conta quantas aulas ocorreram em cada mês
    ).order_by('mes')

    # Prepara os dados para o JavaScript do Chart.js
    chart_labels = [item['mes'].strftime('%b/%Y') for item in aulas_por_mes]
    chart_data = [item['contagem'] for item in aulas_por_mes]
    
    # --- LISTAS DE DETALHES ---
    
    # Lista de todos os professores que já lecionaram esta modalidade
    professores_da_modalidade = CustomUser.objects.filter(
        aula__in=aulas_da_modalidade
    ).distinct().order_by('username')
    
    # Paginação para o histórico de aulas
    aulas_paginadas = Paginator(aulas_da_modalidade.order_by("-data_hora"), 10).get_page(request.GET.get("page"))

    # Monta o contexto final para o template
    contexto = {
        "modalidade": modalidade,
        "titulo": f"Dashboard da Modalidade: {modalidade.nome}",
        
        # KPIs
        "total_aulas": total_aulas,
        "total_realizadas": total_realizadas,
        "alunos_ativos_count": alunos_ativos_count,
        "professores_count": professores_count,
        
        # Dados do Gráfico
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        
        # Listas
        "professores_da_modalidade": professores_da_modalidade,
        "aulas": aulas_paginadas, # Usando a chave 'aulas' para o include da tabela
    }
    
    return render(request, "scheduler/modalidade_detalhe.html", contexto)


# --- VIEWS PARA GERENCIAMENTO DE PROFESSORES ---
@user_passes_test(is_admin)
def listar_professores(request):
    search_query = request.GET.get("q", "")
    now = timezone.now()

    professores_queryset = CustomUser.objects.filter(tipo__in=['professor', 'admin'])

    # --- INÍCIO DA CORREÇÃO ---
    
    # 1. Criamos a Subquery para encontrar a próxima aula
    #    Para cada professor (OuterRef('pk')), ela busca na tabela Aula,
    #    filtra por aulas futuras, ordena pela mais próxima e pega só o valor da data.
    proxima_aula_subquery = Aula.objects.filter(
        professor=OuterRef('pk'), 
        data_hora__gte=now
    ).order_by('data_hora').values('data_hora')[:1]

    # 2. Usamos a Subquery na anotação
    professores_queryset = professores_queryset.annotate(
        total_aulas_realizadas=Count('aulas_validadas_por_mim', distinct=True),
        total_alunos_atendidos=Count('aulas_validadas_por_mim__aula__aluno', distinct=True),
        # A anotação agora usa a Subquery corretamente
        proxima_aula=Subquery(proxima_aula_subquery)
    )

    # --- FIM DA CORREÇÃO ---

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
    professor = get_object_or_404(CustomUser, pk=pk, tipo="professor")
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
    professor = get_object_or_404(CustomUser, pk=pk, tipo="professor")
    if professor.aula_set.exists():
        messages.warning(
            request,
            f'O professor "{professor.username}" está atribuído a {professor.aula_set.count()} aulas. Ao excluí-lo, essas aulas ficarão sem professor atribuído.',
        )

    if request.user.pk == pk:
        messages.error(
            request, "Você não pode excluir seu próprio usuário de administrador."
        )
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
    if not (request.user.tipo == "admin" or (request.user.tipo == "professor" and request.user.pk == pk)):
        messages.error(request, "Você não tem permissão para acessar este perfil.")
        return redirect("scheduler:dashboard")

    professor = get_object_or_404(CustomUser, pk=pk, tipo__in=['professor', 'admin'])
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")
    data_inicial, data_final = None, None
    aulas_relacionadas = Aula.objects.filter(Q(professor=professor) | Q(relatorioaula__professor_que_validou=professor)).distinct()

    # Converte as datas UMA VEZ
    if data_inicial_str:
        try:
            data_inicial = datetime.strptime(data_inicial_str, "%Y-%m-%d").date()
        except ValueError: pass
    if data_final_str:
        try:
            data_final = datetime.strptime(data_final_str, "%Y-%m-%d").date()
        except ValueError: pass
    # --- A PARTIR DAQUI, TODAS AS CONTAGENS USARÃO O QUERYSET JÁ FILTRADO ---
    
    # KPIs de Status de Aulas
    total_aulas_geral = aulas_relacionadas.count()
    total_canceladas = aulas_relacionadas.filter(status="Cancelada").count()
    total_aluno_ausente = aulas_relacionadas.filter(status="Aluno Ausente").count()
    total_agendadas = aulas_relacionadas.filter(status="Agendada").count()

    # NOVA LÓGICA PARA 'AULAS REALIZADAS'
    # Vamos contar diretamente os relatórios validados pelo professor, respeitando os filtros de data
    relatorios_do_professor = RelatorioAula.objects.filter(professor_que_validou=professor)
    if data_inicial:
        aulas_relacionadas = aulas_relacionadas.filter(data_hora__date__gte=data_inicial)
        relatorios_do_professor = relatorios_do_professor.filter(aula__data_hora__date__gte=data_inicial)
    
    if data_final:
        aulas_relacionadas = aulas_relacionadas.filter(data_hora__date__lte=data_final)
        relatorios_do_professor = relatorios_do_professor.filter(aula__data_hora__date__lte=data_final)
   
    
    # A contagem final e precisa
    total_realizadas = relatorios_do_professor.count()

    total_substituido = aulas_relacionadas.filter(
        professor=professor,  # Aulas que foram ATRIBUÍDAS a ele
        status='Realizada'    # E que foram realizadas...
    ).exclude(
        relatorioaula__professor_que_validou=professor # ...mas NÃO por ele.
    ).count()

    # Cálculo da Taxa de Presença
    aulas_contabilizaveis_presenca = total_realizadas + total_aluno_ausente
    taxa_presenca = 0
    if aulas_contabilizaveis_presenca > 0:
        taxa_presenca = (total_realizadas / aulas_contabilizaveis_presenca) * 100

    # Top 3 Alunos com mais aulas
    top_alunos = (
        aulas_relacionadas.values("aluno__nome_completo")
        .annotate(contagem=Count("aluno"))
        .order_by("-contagem")[:3]
    )

    # Top 3 Modalidades mais lecionadas
    top_modalidades = (
        aulas_relacionadas.values("modalidade__nome")
        .annotate(contagem=Count("modalidade"))
        .order_by("-contagem")[:3]
    )

    # Paginação (o queryset já está filtrado)
    aulas_do_professor_paginated = Paginator(aulas_relacionadas.order_by("-data_hora"), 5).get_page(request.GET.get("page"))

    # Contexto final com os novos dados
    contexto = {
        "professor": professor,
        "titulo": f"Dashboard do Professor: {professor.username}",
        "aulas_do_professor": aulas_do_professor_paginated,
        
        # Passa os valores do filtro de volta para o template
        "data_inicial": data_inicial_str,
        "data_final": data_final_str,
        
        # KPIs
        "total_aulas_geral": total_aulas_geral,
        "total_realizadas": total_realizadas,
        "total_canceladas": total_canceladas,
        "total_aluno_ausente": total_aluno_ausente,
        "total_agendadas": total_agendadas,
        "total_substituido": total_substituido,
        "taxa_presenca": taxa_presenca,

        # Listas
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
    Retorna um dicionário com todos os dados calculados.
    """
    # Parâmetros de filtro
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")
    professor_filtro_id = request.GET.get("professor_filtro", "")
    modalidade_filtro_id = request.GET.get("modalidade_filtro", "")
    status_filtro = request.GET.get("status_filtro", "")

    aulas_base_queryset = Aula.objects.all()

    # Aplica filtros (lógica que você já tem)
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
    if professor_filtro_id:
        aulas_base_queryset = aulas_base_queryset.filter(Q(professor_id=professor_filtro_id) | Q(relatorioaula__professor_que_validou_id=professor_filtro_id))
    if modalidade_filtro_id:
        aulas_base_queryset = aulas_base_queryset.filter(modalidade_id=modalidade_filtro_id)
    if status_filtro:
        aulas_base_queryset = aulas_base_queryset.filter(status=status_filtro)

    # Agregações (lógica que você já tem)
    aulas_por_professor_final = list(aulas_base_queryset.values('relatorioaula__professor_que_validou__username').annotate(aulas_realizadas=Count('id')).order_by('-aulas_realizadas').values('relatorioaula__professor_que_validou__username', 'aulas_realizadas'))
    aulas_por_modalidade_final = list(aulas_base_queryset.values('modalidade__nome').annotate(total_aulas=Count('id'), aulas_realizadas=Count('id', filter=Q(status='Realizada'))).order_by('-total_aulas').values('modalidade__nome', 'total_aulas', 'aulas_realizadas'))

    # Retorna um dicionário com todos os dados
    return {
        "aulas_por_professor": aulas_por_professor_final,
        "aulas_por_modalidade": aulas_por_modalidade_final,
    }


@user_passes_test(is_admin)
def relatorios_aulas(request):
    # --- Seção 1: Obtenção de filtros da URL ---
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")
    professor_filtro_id = request.GET.get("professor_filtro", "")
    modalidade_filtro_id = request.GET.get("modalidade_filtro", "")
    status_filtro = request.GET.get("status_filtro", "")

    # --- Seção 2: Queryset base e aplicação de filtros ---
    aulas_base_queryset = Aula.objects.all()

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
    if professor_filtro_id:
        aulas_base_queryset = aulas_base_queryset.filter(Q(professor_id=professor_filtro_id) | Q(relatorioaula__professor_que_validou_id=professor_filtro_id))
    if modalidade_filtro_id:
        aulas_base_queryset = aulas_base_queryset.filter(modalidade_id=modalidade_filtro_id)
    
    # Lógica de filtro de status condicional
    if status_filtro:
        if status_filtro == 'Substituído':
            aulas_base_queryset = aulas_base_queryset.filter(
                status='Realizada', professor__isnull=False, relatorioaula__professor_que_validou__isnull=False
            ).exclude(professor=F('relatorioaula__professor_que_validou'))
        else:
            aulas_base_queryset = aulas_base_queryset.filter(status=status_filtro)

    # --- Seção 3: Cálculo dos KPIs e dados agregados ---
    
    # KPIs para os cards e gráfico de pizza
    total_aulas = aulas_base_queryset.count()
    total_realizadas_bruto = aulas_base_queryset.filter(status="Realizada").count()
    total_canceladas = aulas_base_queryset.filter(status="Cancelada").count()
    total_aluno_ausente = aulas_base_queryset.filter(status="Aluno Ausente").count()
    total_agendadas = aulas_base_queryset.filter(status="Agendada").count()
    
    total_substituidas = aulas_base_queryset.filter(
        status='Realizada', professor__isnull=False, relatorioaula__professor_que_validou__isnull=False
    ).exclude(professor=F('relatorioaula__professor_que_validou')).count()

    # Agregação para a tabela de Professores
    professores = CustomUser.objects.filter(tipo__in=['professor', 'admin'])
    aulas_por_professor_final = professores.annotate(
        total_atribuidas=Count('aula', distinct=True, filter=Q(aula__in=aulas_base_queryset)),
        total_realizadas=Count('aulas_validadas_por_mim', distinct=True, filter=Q(aulas_validadas_por_mim__aula__in=aulas_base_queryset))
    ).filter(Q(total_atribuidas__gt=0) | Q(total_realizadas__gt=0)).order_by('-total_realizadas', '-total_atribuidas')

    # Agregação para a tabela de Modalidades
    aulas_por_modalidade_final = list(aulas_base_queryset.filter(modalidade__isnull=False).values('modalidade__id', 'modalidade__nome').annotate(total_aulas=Count('id'), aulas_realizadas=Count('id', filter=Q(status='Realizada'))).order_by('-total_aulas'))

    # Preparação de dados para o Gráfico de Barras
    prof_chart_labels = [prof.username.title() for prof in aulas_por_professor_final]
    prof_chart_data_realizadas = [prof.total_realizadas for prof in aulas_por_professor_final]
    
    # --- Seção 4: Montagem do contexto final ---
    professores_list = CustomUser.objects.filter(tipo__in=["professor", "admin"]).order_by("username")
    modalidades_list = Modalidade.objects.all().order_by("nome")
    status_choices = Aula.STATUS_AULA_CHOICES

    contexto = {
        "titulo": "Relatórios de Aulas",
        "data_inicial": data_inicial_str,
        "data_final": data_final_str,
        "professor_filtro": professor_filtro_id,
        "modalidade_filtro": modalidade_filtro_id,
        "status_filtro": status_filtro,
        "professores_list": professores_list,
        "modalidades_list": modalidades_list,
        "status_choices": status_choices,
        
        # KPIs para os cards e gráfico
        "total_aulas": total_aulas,
        "total_agendadas": total_agendadas,
        "total_realizadas": total_realizadas_bruto, # Envia o total bruto
        "total_canceladas": total_canceladas,
        "total_aluno_ausente": total_aluno_ausente,
        "total_substituidas": total_substituidas,    # Envia o detalhe das substituições
        
        # Dados para as tabelas
        "aulas_por_professor": aulas_por_professor_final,
        "aulas_por_modalidade": aulas_por_modalidade_final,
        
        # Dados para o gráfico de barras
        "prof_chart_labels": prof_chart_labels,
        "prof_chart_data_realizadas": prof_chart_data_realizadas,
    }
    return render(request, "scheduler/relatorios_aulas.html", contexto)


# --- NOVA VIEW DE EXPORTAÇÃO ---
@user_passes_test(is_admin)
def exportar_relatorio_agregado(request):
    # 1. Chama a MESMA função auxiliar para obter os dados já filtrados
    dados = _get_dados_relatorio_agregado(request)
    
    # 2. Prepara a resposta HTTP para ser um arquivo CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_gerencial.csv"'
    response.write(u'\ufeff'.encode('utf8')) # BOM para caracteres PT-BR no Excel

    writer = csv.writer(response, delimiter=';')

    # 3. Escreve os dados de "Aulas por Professor"
    writer.writerow(['Professor', 'Aulas Realizadas'])
    for item in dados['aulas_por_professor']:
        writer.writerow([
            item['relatorioaula__professor_que_validou__username'],
            item['aulas_realizadas']
        ])
        
    writer.writerow([]) # Linha em branco para separar as tabelas

    # 4. Escreve os dados de "Aulas por Modalidade"
    writer.writerow(['Modalidade', 'Total de Aulas', 'Aulas Realizadas'])
    for item in dados['aulas_por_modalidade']:
        writer.writerow([
            item['modalidade__nome'],
            item['total_aulas'],
            item['aulas_realizadas']
        ])

    return response


# --- NOVA VIEW PARA EXPORTAÇÃO DE DADOS ---
@user_passes_test(is_admin)  # Apenas administradores podem exportar dados
def exportar_aulas(request):
    # Reutiliza a lógica de filtragem da listar_aulas para que a exportação seja filtrada
    order_by = request.GET.get("order_by", "data_hora")
    direction = request.GET.get("direction", "asc")
    search_query = request.GET.get("q", "")
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")

    # Mapeamento de campos de exibição para campos de modelo
    valid_order_fields = {
        "aluno": "aluno__nome_completo",
        "modalidade": "modalidade__nome",
        "professor_atribuido": "professor__username",
        "professor_realizou": "relatorioaula__professor_que_validou__username",
        "data_hora": "data_hora",
        "status": "status",
    }

    if order_by not in valid_order_fields:
        order_by = "data_hora"

    order_field = valid_order_fields[order_by]

    if direction == "desc":
        order_field = "-" + order_field

    aulas_queryset = Aula.objects.all()

    if search_query:
        aulas_queryset = aulas_queryset.filter(
            Q(aluno__nome_completo__icontains=search_query)
            | Q(professor__username__icontains=search_query)
            | Q(modalidade__nome__icontains=search_query)
            | Q(status__icontains=search_query)
            | Q(relatorioaula__professor_que_validou__username__icontains=search_query)
        )

    if data_inicial_str:
        try:
            data_inicial = datetime.strptime(data_inicial_str, "%Y-%m-%d").date()
            aulas_queryset = aulas_queryset.filter(data_hora__date__gte=data_inicial)
        except ValueError:
            messages.error(request, "Formato de Data Inicial inválido. Use AAAA-MM-DD.")

    if data_final_str:
        try:
            data_final = datetime.strptime(data_final_str, "%Y-%m-%d").date()
            aulas_queryset = aulas_queryset.filter(data_hora__date__lte=data_final)
        except ValueError:
            messages.error(request, "Formato de Data Final inválido. Use AAAA-MM-DD.")

    aulas = aulas_queryset.order_by(order_field)

    # Cria a resposta HTTP com cabeçalhos para download de CSV
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="aulas_exportadas.csv"'

    writer = csv.writer(
        response, delimiter=";"
    )  # Use ';' como delimitador para compatibilidade com Excel em PT-BR

    # Escreve o cabeçalho do CSV
    writer.writerow(
        [
            "ID",
            "Aluno",
            "Modalidade",
            "Professor Atribuído",
            "Professor Realizou",
            "Data e Hora",
            "Status",
            "Conteúdo Teórico",
            "Observações Gerais",
        ]
    )

    # Escreve os dados das aulas
    for aula in aulas:
        # Pega o relatório da aula se existir, para pegar o professor que realizou e observações
        relatorio = getattr(
            aula, "relatorioaula", None
        )  # Pega o objeto relatorioaula se existir

        professor_realizou = (
            relatorio.professor_que_validou.username
            if relatorio and relatorio.professor_que_validou
            else "N/A"
        )
        conteudo_teorico = relatorio.conteudo_teorico if relatorio else ""
        observacoes_gerais = relatorio.observacoes_gerais if relatorio else ""

        writer.writerow(
            [
                aula.id,
                aula.aluno.nome_completo,
                aula.modalidade.nome,
                aula.professor.username if aula.professor else "N/A",
                professor_realizou,
                aula.data_hora.strftime("%Y-%m-%d %H:%M"),
                aula.status,
                conteudo_teorico,
                observacoes_gerais,
            ]
        )

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

    if start_str and end_str:
        try:
            start_date = datetime.fromisoformat(start_str.replace("Z", "+00:00")).date()
            end_date = datetime.fromisoformat(end_str.replace("Z", "+00:00")).date()

            aulas_no_periodo = Aula.objects.filter(data_hora__date__range=(start_date, end_date))

            # A lógica de filtro por professor continua a mesma...
            if request.user.tipo == "professor":
                aulas_no_periodo = aulas_no_periodo.filter(Q(professor=request.user) | Q(relatorioaula__professor_que_validou=request.user))
            elif request.user.tipo == "admin" and professor_filtro_id:
                aulas_no_periodo = aulas_no_periodo.filter(Q(professor_id=professor_filtro_id) | Q(relatorioaula__professor_que_validou_id=professor_filtro_id))
            
            aulas_no_periodo = aulas_no_periodo.select_related(
                "aluno", "professor", "modalidade", "relatorioaula", "relatorioaula__professor_que_validou"
            ).distinct()

            for aula in aulas_no_periodo:
                # Pega apenas o primeiro nome do aluno para economizar espaço
                primeiro_nome_aluno = aula.aluno.nome_completo.split()[0].title()
                title = f"{primeiro_nome_aluno} ({aula.modalidade.nome.title()})"
                # --- FIM DA MUDANÇA ---

                # O resto da lógica para extendedProps e classNames continua igual
                event_class = f'status-{aula.status.replace(" ", "")}'
                professor_realizou = getattr(aula, 'relatorioaula', None) and getattr(aula.relatorioaula, 'professor_que_validou', None)
                
                events.append({
                    "title": title, # <-- Usamos o novo título simplificado
                    "start": aula.data_hora.isoformat(),
                    "url": f"/aula/{aula.pk}/validar/",
                    "classNames": [event_class],
                    "extendedProps": {
                        "status": aula.status,
                        "aluno": aula.aluno.nome_completo,
                        "professor_atribuido": aula.professor.username if aula.professor else "N/A",
                        "professor_realizou": professor_realizou.username if professor_realizou else "N/A",
                        "modalidade": aula.modalidade.nome,
                    },
                })

            return JsonResponse(events, safe=False)
        except (ValueError, TypeError) as e:
            return JsonResponse({"error": f"Dados de data inválidos ou erro interno: {e}"}, status=400)

    return JsonResponse({"error": "Período não fornecido."}, status=400)
