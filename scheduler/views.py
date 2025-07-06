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
from django.db.models import Q, Count
from datetime import datetime
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
    # Parâmetros de ordenação e busca existentes
    order_by = request.GET.get("order_by", "data_hora")
    direction = request.GET.get("direction", "asc")
    search_query = request.GET.get("q", "")
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")

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

    aulas_queryset = Aula.objects.filter(status="Agendada")

    if search_query:
        aulas_queryset = aulas_queryset.filter(
            Q(aluno__nome_completo__icontains=search_query)
            | Q(professor__username__icontains=search_query)
            | Q(modalidade__nome__icontains=search_query)
            | Q(status__icontains=search_query)
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

    aulas_queryset = aulas_queryset.order_by(order_field)

    paginator = Paginator(aulas_queryset, 10)
    page = request.GET.get("page")
    try:
        aulas = paginator.page(page)
    except PageNotAnInteger:
        aulas = paginator.page(1)
    except EmptyPage:
        aulas = paginator.page(paginator.num_pages)

    contexto = {
        "aulas": aulas,
        "is_admin": request.user.tipo == "admin",
        "order_by": order_by,
        "direction": direction,
        "search_query": search_query,
        "data_inicial": data_inicial_str,
        "data_final": data_final_str,
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


# --- VIEWS DE GERENCIAMENTO DE ALUNOS ---
@user_passes_test(is_admin)
def listar_alunos(request):
    alunos = Aluno.objects.all().order_by("nome_completo")
    contexto = {"alunos": alunos, "titulo": "Gerenciamento de Alunos"}
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
    aulas_do_aluno = Aula.objects.filter(aluno=aluno).order_by("-data_hora")

    paginator = Paginator(aulas_do_aluno, 5)
    page = request.GET.get("page")
    try:
        aulas_do_aluno_paginated = paginator.page(page)
    except PageNotAnInteger:
        aulas_do_aluno_paginated = paginator.page(1)
    except EmptyPage:
        aulas_do_aluno_paginated = paginator.page(paginator.num_pages)

    contexto = {
        "aluno": aluno,
        "aulas_do_aluno": aulas_do_aluno_paginated,
        "titulo": f"Perfil do Aluno: {aluno.nome_completo}",
    }
    return render(request, "scheduler/aluno_detalhe.html", contexto)


@login_required
def listar_aulas(request):
    # Parâmetros de ordenação e busca existentes
    order_by = request.GET.get("order_by", "data_hora")
    direction = request.GET.get("direction", "asc")
    search_query = request.GET.get("q", "")
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")

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

    # AULAS_QUERYSET AJUSTADO AQUI
    if request.user.tipo == "admin":
        aulas_queryset = Aula.objects.all()  # Admin vê todas
        contexto_titulo = "Histórico Geral de Aulas"
    else:  # Se não for admin, é professor
        # Professor vê APENAS as aulas atribuídas a ele OU que ele realizou
        aulas_queryset = Aula.objects.filter(
            Q(professor=request.user)
            | Q(relatorioaula__professor_que_validou=request.user)
        )
        contexto_titulo = "Meu Histórico de Aulas"

    # Aplica o filtro de busca textual se houver um termo
    if search_query:
        aulas_queryset = aulas_queryset.filter(
            Q(aluno__nome_completo__icontains=search_query)
            | Q(professor__username__icontains=search_query)
            | Q(modalidade__nome__icontains=search_query)
            | Q(status__icontains=search_query)
            # A busca no professor_que_validou é importante aqui também
            | Q(relatorioaula__professor_que_validou__username__icontains=search_query)
        )

    # Aplica o filtro de data se houver data_inicial e/ou data_final
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

    aulas_queryset = aulas_queryset.order_by(order_field)

    paginator = Paginator(aulas_queryset, 10)
    page = request.GET.get("page")
    try:
        aulas = paginator.page(page)
    except PageNotAnInteger:
        aulas = paginator.page(1)
    except EmptyPage:
        aulas = paginator.page(paginator.num_pages)

    contexto = {
        "aulas": aulas,
        "titulo": contexto_titulo,  # Título dinâmico
        "order_by": order_by,
        "direction": direction,
        "search_query": search_query,
        "data_inicial": data_inicial_str,
        "data_final": data_final_str,
    }

    # Removemos o if request.user.tipo != "admin" para o título aqui, já que ele está dentro do filtro aulas_queryset

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
    modalidades = Modalidade.objects.all().order_by("nome")
    contexto = {"modalidades": modalidades, "titulo": "Gerenciamento de Modalidades"}
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


# --- VIEWS PARA GERENCIAMENTO DE PROFESSORES ---
# ... (listar_professores, editar_professor, excluir_professor) ...
@user_passes_test(is_admin)
def listar_professores(request):
    professores = CustomUser.objects.filter(tipo="professor").order_by("username")
    contexto = {"professores": professores, "titulo": "Gerenciamento de Professores"}
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
    # Garante que apenas usuários do tipo 'professor' podem ter um perfil detalhado
    # Ou um admin pode ver o perfil de qualquer professor
    if not (
        request.user.tipo == "admin"
        or (request.user.tipo == "professor" and request.user.pk == pk)
    ):
        messages.error(request, "Você não tem permissão para acessar este perfil.")
        return redirect("scheduler:dashboard")  # Ou outra página de erro/acesso negado

    professor = get_object_or_404(CustomUser, pk=pk, tipo="professor")

    # Busca todas as aulas onde este professor é o 'atribuído' OU o 'realizou'
    # Usamos Q objects para o filtro OR
    aulas_do_professor = Aula.objects.filter(
        Q(professor=professor) | Q(relatorioaula__professor_que_validou=professor)
    ).order_by(
        "-data_hora"
    )  # Ordena as aulas pela data mais recente primeiro

    # Contagem de aulas ATRIBUÍDAS
    total_aulas_atribuidas = Aula.objects.filter(professor=professor).count()

    # Contagem de aulas REALIZADAS (validadas)
    total_aulas_realizadas = RelatorioAula.objects.filter(
        professor_que_validou=professor
    ).count()

    # Paginação das aulas do professor
    paginator = Paginator(
        aulas_do_professor, 5
    )  # 5 aulas por página, ajuste conforme necessário
    page = request.GET.get("page")
    try:
        aulas_do_professor_paginated = paginator.page(page)
    except PageNotAnInteger:
        aulas_do_professor_paginated = paginator.page(1)
    except EmptyPage:
        aulas_do_professor_paginated = paginator.page(paginator.num_pages)

    contexto = {
        "professor": professor,
        "aulas_do_professor": aulas_do_professor_paginated,  # Passa o objeto Page paginado
        "titulo": f"Perfil do Professor: {professor.username}",
        "total_aulas_atribuidas": total_aulas_atribuidas,  # NOVO
        "total_aulas_realizadas": total_aulas_realizadas,  # NOVO
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


@user_passes_test(is_admin)  # Apenas administradores podem gerenciar modalidades
def relatorios_aulas(request):
    # Parâmetros de filtro
    data_inicial_str = request.GET.get("data_inicial", "")
    data_final_str = request.GET.get("data_final", "")
    professor_filtro_id = request.GET.get("professor_filtro", "")
    modalidade_filtro_id = request.GET.get("modalidade_filtro", "")
    status_filtro = request.GET.get("status_filtro", "")

    # Queryset base para todas as aulas, ANTES dos filtros específicos do relatório
    # Isso garante que as contagens totais e por professor/modalidade
    # respeitem os filtros de data, professor, modalidade e status.
    aulas_base_queryset = Aula.objects.all()

    # Aplica filtros de data
    if data_inicial_str:
        try:
            data_inicial = datetime.strptime(data_inicial_str, "%Y-%m-%d").date()
            aulas_base_queryset = aulas_base_queryset.filter(
                data_hora__date__gte=data_inicial
            )
        except ValueError:
            messages.error(request, "Formato de Data Inicial inválido. Use AAAA-MM-DD.")
            data_inicial_str = ""

    if data_final_str:
        try:
            data_final = datetime.strptime(data_final_str, "%Y-%m-%d").date()
            aulas_base_queryset = aulas_base_queryset.filter(
                data_hora__date__lte=data_final
            )
        except ValueError:
            messages.error(request, "Formato de Data Final inválido. Use AAAA-MM-DD.")
            data_final_str = ""

    # Aplica filtros de professor, modalidade e status (esses filtros já estavam na função)
    if professor_filtro_id:
        aulas_base_queryset = aulas_base_queryset.filter(
            Q(professor_id=professor_filtro_id)
            | Q(relatorioaula__professor_que_validou_id=professor_filtro_id)
        )

    if modalidade_filtro_id:
        aulas_base_queryset = aulas_base_queryset.filter(
            modalidade_id=modalidade_filtro_id
        )

    if status_filtro:
        aulas_base_queryset = aulas_base_queryset.filter(status=status_filtro)

    # --- NOVO: Agregações para os Relatórios ---

    # 1. Resumo Geral de Aulas (contagem total e por status)
    total_aulas = aulas_base_queryset.count()
    total_agendadas = aulas_base_queryset.filter(status="Agendada").count()
    total_realizadas = aulas_base_queryset.filter(status="Realizada").count()
    total_canceladas = aulas_base_queryset.filter(status="Cancelada").count()
    total_aluno_ausente = aulas_base_queryset.filter(status="Aluno Ausente").count()

    # 2. Aulas por Professor (CORRIGIDO)
    # Agrupa por professor atribuído E por professor que realizou, depois unifica

    # Aulas atribuídas
    aulas_atrib_por_prof = (
        aulas_base_queryset.values("professor", "professor__username")
        .annotate(count=Count("id"))
        .order_by("professor__username")
    )

    # Aulas realizadas (validadas)
    aulas_real_por_prof = (
        aulas_base_queryset.filter(
            relatorioaula__professor_que_validou__isnull=False, status="Realizada"
        )
        .values(
            "relatorioaula__professor_que_validou",
            "relatorioaula__professor_que_validou__username",
        )
        .annotate(count=Count("id"))
        .order_by("relatorioaula__professor_que_validou__username")
    )

    # Combinar os resultados
    aulas_por_professor_combinado = {}
    for item in aulas_atrib_por_prof:
        prof_id = item["professor"]
        if prof_id:  # Ignora aulas sem professor atribuído
            prof_username = item["professor__username"]
            aulas_por_professor_combinado.setdefault(
                prof_id,
                {
                    "professor_id": prof_id,
                    "professor_username": prof_username,
                    "total_aulas": 0,
                    "aulas_realizadas": 0,
                },
            )
            aulas_por_professor_combinado[prof_id]["total_aulas"] += item[
                "count"
            ]  # Soma as atribuídas

    for item in aulas_real_por_prof:
        prof_id = item["relatorioaula__professor_que_validou"]
        prof_username = item["relatorioaula__professor_que_validou__username"]
        aulas_por_professor_combinado.setdefault(
            prof_id,
            {
                "professor_id": prof_id,
                "professor_username": prof_username,
                "total_aulas": 0,
                "aulas_realizadas": 0,
            },
        )
        aulas_por_professor_combinado[prof_id]["total_aulas"] += item[
            "count"
        ]  # Soma as realizadas
        aulas_por_professor_combinado[prof_id]["aulas_realizadas"] += item["count"]

    # Converter o dicionário de volta para uma lista de valores
    aulas_por_professor_final = sorted(
        aulas_por_professor_combinado.values(),
        key=lambda x: x["professor_username"] if x["professor_username"] else "",
    )

    # 3. Aulas por Modalidade (CORRIGIDO)
    # Garante que 'N/A' seja tratado como uma modalidade sem nome, ou que aulas sem modalidade sejam filtradas
    # Supondo que modalidade_id não seja nulo devido a on_delete=PROTECT
    aulas_por_modalidade_query = (
        aulas_base_queryset.values("modalidade__nome", "modalidade__id")
        .annotate(
            total_aulas=Count("id"),
            aulas_realizadas=Count("id", filter=Q(status="Realizada")),
        )
        .order_by("modalidade__nome")
    )

    # Filtrar qualquer entrada onde modalidade__id possa ser None (embora PROTECT deva impedir)
    # Se ainda aparecer N/A, pode ser que a aula foi criada sem modalidade antes do PROTECT.
    aulas_por_modalidade_final = [
        item
        for item in aulas_por_modalidade_query
        if item["modalidade__id"] is not None
    ]

    # --- FIM Agregações ---

    # Obtém todas as modalidades e professores para popular os dropdowns de filtro
    professores_list = CustomUser.objects.filter(tipo="professor").order_by("username")
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
        "total_aulas": total_aulas,
        "total_agendadas": total_agendadas,
        "total_realizadas": total_realizadas,
        "total_canceladas": total_canceladas,
        "total_aluno_ausente": total_aluno_ausente,
        "aulas_por_professor": aulas_por_professor_final,  # CORRIGIDO
        "aulas_por_modalidade": aulas_por_modalidade_final,  # CORRIGIDO
    }
    return render(request, "scheduler/relatorios_aulas.html", contexto)


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

            aulas_no_periodo = Aula.objects.filter(
                data_hora__date__range=(start_date, end_date)
            )

            if request.user.tipo == "professor":
                aulas_no_periodo = aulas_no_periodo.filter(
                    Q(professor=request.user)
                    | Q(relatorioaula__professor_que_validou=request.user)
                )
            elif request.user.tipo == "admin" and professor_filtro_id:
                professor_filtro_id = int(professor_filtro_id)
                aulas_no_periodo = aulas_no_periodo.filter(
                    Q(professor_id=professor_filtro_id)
                    | Q(relatorioaula__professor_que_validou_id=professor_filtro_id)
                )
            elif request.user.tipo == "admin" and not professor_filtro_id:
                pass

            aulas_no_periodo = aulas_no_periodo.select_related(
                "aluno",
                "professor",
                "modalidade",
                "relatorioaula",
                "relatorioaula__professor_que_validou",
            )

            for aula in aulas_no_periodo:
                title_parts = [
                    f"{aula.modalidade.nome.title()} ({aula.aluno.nome_completo.title()})"
                ]
                if aula.professor:
                    title_parts.append(
                        f"Prof: {aula.professor.username.title()}"
                    )

                relatorio_aula_obj = getattr(aula, "relatorioaula", None)
                professor_que_validou_username = "N/A"
                if relatorio_aula_obj and relatorio_aula_obj.professor_que_validou:
                    professor_que_validou_username = (
                        relatorio_aula_obj.professor_que_validou.username.title()
                    )
                    if (
                        aula.professor
                        and relatorio_aula_obj.professor_que_validou != aula.professor
                    ):
                        title_parts.append(
                            f"Realizado por: {professor_que_validou_username}"
                        )

                event_class = f'status-{aula.status.replace(" ", "")}'

                events.append(
                    {
                        "title": "\n".join(
                            title_parts
                        ),  # <--- AQUI O '\n' É USADO PARA JUNTAR AS PARTES DO TÍTULO
                        "start": aula.data_hora.isoformat(),
                        "url": f"/aula/{aula.pk}/validar/",
                        "classNames": [event_class],
                        "extendedProps": {
                            "status": aula.status,
                            "aluno": aula.aluno.nome_completo,
                            "professor_atribuido": (
                                aula.professor.username if aula.professor else "N/A"
                            ),
                            "professor_realizou": professor_que_validou_username,
                            "modalidade": aula.modalidade.nome,
                        },
                    }
                )

            return JsonResponse(events, safe=False)

        except (ValueError, TypeError) as e:
            return JsonResponse(
                {"error": f"Dados de data inválidos ou erro interno: {e}"}, status=400
            )

    return JsonResponse({"error": "Período não fornecido."}, status=400)
