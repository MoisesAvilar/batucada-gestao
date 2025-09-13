from django.apps import apps
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import (
    Transaction,
    Despesa,
    Receita,
    DespesaRecorrente,
    ReceitaRecorrente,
    Category,
)
from .forms import (
    TransactionForm,
    CategoryForm,
    DespesaForm,
    DespesaRecorrenteForm,
    ReceitaRecorrenteForm,
    MensalidadeReceitaForm,
    VendaReceitaForm,
)
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.forms.models import model_to_dict
from django.db.models import Sum
from django.db import transaction
from django.core.paginator import Paginator  # <<< ADICIONADO
from datetime import date, timedelta, datetime
from django.db.models import Q
from scheduler.models import Aula, CustomUser, Modalidade, PresencaAluno
from django.utils.timezone import now
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from scheduler.models import Aluno

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.styles import Border, Side
from openpyxl.cell.rich_text import TextBlock, Text
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if getattr(request.user, "tipo", None) == "admin":
            return view_func(request, *args, **kwargs)
        return redirect("scheduler:dashboard")

    return wrapper


def add_months(start_date, months):
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(
        start_date.day, [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
    )
    return date(year, month, day)


@admin_required
def transaction_list_view(request):
    MESES_PT = {
        1: "Jan",
        2: "Fev",
        3: "Mar",
        4: "Abr",
        5: "Mai",
        6: "Jun",
        7: "Jul",
        8: "Ago",
        9: "Set",
        10: "Out",
        11: "Nov",
        12: "Dez",
    }
    unidade_ativa_id = request.session.get("unidade_ativa_id")
    if not unidade_ativa_id:
        messages.warning(request, "Selecione uma Unidade de Negócio.")
        return redirect("scheduler:dashboard")

    today = now().date()
    start_date = (
        date.fromisoformat(request.GET.get("start_date"))
        if request.GET.get("start_date")
        else today.replace(day=1)
    )
    end_date = (
        date.fromisoformat(request.GET.get("end_date"))
        if request.GET.get("end_date")
        else (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        - timedelta(days=1)
    )

    total_a_pagar = (
        Despesa.objects.filter(
            unidade_negocio_id=unidade_ativa_id,
            status="a_pagar",
            data_competencia__range=[start_date, end_date],
        ).aggregate(total=Sum("valor"))["total"]
        or 0
    )

    total_a_receber = (
        Receita.objects.filter(
            unidade_negocio_id=unidade_ativa_id,
            status="a_receber",
            data_competencia__range=[start_date, end_date],
        ).aggregate(total=Sum("valor"))["total"]
        or 0
    )

    transactions = Transaction.objects.filter(
        unidade_negocio_id=unidade_ativa_id,
        transaction_date__range=[start_date, end_date],
    ).select_related("category")

    total_income = (
        transactions.filter(category__type="income").aggregate(total=Sum("amount"))[
            "total"
        ]
        or 0
    )
    total_expenses = (
        transactions.filter(category__type="expense").aggregate(total=Sum("amount"))[
            "total"
        ]
        or 0
    )
    balance = total_income - total_expenses

    expenses_by_category = (
        transactions.filter(category__type="expense")
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    chart_labels = [item["category__name"] for item in expenses_by_category]
    chart_data = [float(item["total"]) for item in expenses_by_category]

    months_spanned = max(
        1,
        (end_date.year - start_date.year) * 12
        + (end_date.month - start_date.month)
        + 1,
    )
    avg_monthly_income = Decimal(total_income) / months_spanned
    avg_monthly_expenses = Decimal(total_expenses) / months_spanned
    cumulative_balance = balance
    monthly_net = avg_monthly_income - avg_monthly_expenses

    projection_data = []
    for i in range(1, 7):
        future_date = add_months(end_date.replace(day=1), i)
        cumulative_balance += monthly_net
        projection_data.append(
            {
                "month": f"{MESES_PT[future_date.month]}/{future_date.year}",
                "income": avg_monthly_income,
                "expenses": avg_monthly_expenses,
                "balance": cumulative_balance,
            }
        )

    paginator = Paginator(transactions, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    form = TransactionForm(initial={"unidade_negocio": unidade_ativa_id})
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            t = form.save(commit=False)
            t.created_by = request.user
            t.unidade_negocio_id = unidade_ativa_id
            t.save()
            messages.success(request, "Lançamento adicionado com sucesso!")
            return redirect(request.get_full_path())

    return render(
        request,
        "finances/transaction_list.html",
        {
            "page_obj": page_obj,
            "form": form,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": balance,
            "start_date": start_date,
            "end_date": end_date,
            "chart_labels": chart_labels,
            "chart_data": chart_data,
            "projection_data": projection_data,
            "total_a_pagar": total_a_pagar,
            "total_a_receber": total_a_receber,
        },
    )


@admin_required
def add_category_ajax(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            return JsonResponse(
                {"status": "success", "id": category.id, "name": category.name}
            )
        else:
            return JsonResponse({"status": "error", "errors": form.errors})
    return JsonResponse({"status": "error", "message": "Invalid request method"})


@admin_required
@require_POST
def add_mensalidade(request):
    """
    View dedicada para adicionar MENSALIDADE, seguindo os padrões do projeto.
    """
    unidade_ativa_id = request.session.get("unidade_ativa_id")
    if not unidade_ativa_id:
        messages.error(
            request, "Sessão expirada ou nenhuma unidade de negócio selecionada."
        )
        return redirect("finances:receita_list")

    form = MensalidadeReceitaForm(request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                receita = form.save(commit=False)
                receita.unidade_negocio_id = unidade_ativa_id  # Padrão do projeto

                # Se já foi recebido, cria a transação e atualiza o status
                if receita.data_recebimento:
                    receita.status = "recebido"
                    transacao = Transaction.objects.create(
                        unidade_negocio_id=unidade_ativa_id,
                        description=f"Recebimento: {receita.descricao}",
                        amount=receita.valor,
                        category=receita.categoria,
                        transaction_date=receita.data_recebimento,
                        student=receita.aluno,
                        created_by=request.user,
                    )
                    receita.transacao = transacao

                receita.save()
                messages.success(request, "Mensalidade adicionada com sucesso!")

        except Exception as e:
            messages.error(request, f"Ocorreu um erro inesperado: {e}")
    else:
        erros = ". ".join(
            [f"{field}: {error[0]}" for field, error in form.errors.items()]
        )
        messages.error(request, f"Erro ao adicionar mensalidade: {erros}")

    return redirect("finances:receita_list")


@admin_required
@require_POST
def add_venda(request):
    """
    View dedicada para adicionar VENDA, seguindo os padrões do projeto.
    """
    unidade_ativa_id = request.session.get("unidade_ativa_id")
    if not unidade_ativa_id:
        messages.error(
            request, "Sessão expirada ou nenhuma unidade de negócio selecionada."
        )
        return redirect("finances:receita_list")

    form = VendaReceitaForm(request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                receita = form.save(commit=False)
                receita.unidade_negocio_id = unidade_ativa_id

                produto = receita.produto
                quantidade_vendida = receita.quantidade

                if produto.quantidade_em_estoque < quantidade_vendida:
                    messages.error(
                        request, f"Estoque insuficiente para '{produto.nome}'."
                    )
                    return redirect("finances:receita_list")

                produto.quantidade_em_estoque -= quantidade_vendida
                produto.save()

                # Se já foi recebido, cria a transação e atualiza o status
                if receita.data_recebimento:
                    receita.status = "recebido"
                    transacao = Transaction.objects.create(
                        unidade_negocio_id=unidade_ativa_id,
                        description=f"Recebimento: {receita.descricao}",
                        amount=receita.valor,
                        category=receita.categoria,
                        transaction_date=receita.data_recebimento,
                        student=receita.aluno,
                        created_by=request.user,
                    )
                    receita.transacao = transacao

                receita.save()
                messages.success(
                    request,
                    f'Venda de "{produto.nome}" registrada e estoque atualizado!',
                )

        except Exception as e:
            messages.error(request, f"Ocorreu um erro inesperado: {e}")
    else:
        erros = ". ".join(
            [f"{field}: {error[0]}" for field, error in form.errors.items()]
        )
        messages.error(request, f"Erro ao registrar venda: {erros}")

    return redirect("finances:receita_list")


@admin_required
def delete_transaction_view(request, pk):
    if request.method == "POST":
        transaction = get_object_or_404(Transaction, pk=pk)
        transaction.delete()
        messages.success(request, "Lançamento deletado com sucesso!")
    return redirect("finances:transaction_list")


@admin_required
def edit_transaction_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == "POST":
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            updated_transaction = form.save()

            data = model_to_dict(updated_transaction)
            data["category_name"] = updated_transaction.category.name
            data["student_name"] = (
                updated_transaction.student.nome_completo
                if updated_transaction.student
                else ""
            )
            data["professor_name"] = (
                updated_transaction.professor.username
                if updated_transaction.professor
                else ""
            )

            return JsonResponse({"status": "success", "transaction": data})
        else:
            return JsonResponse({"status": "error", "errors": form.errors})

    data = {
        "id": transaction.id,
        "description": transaction.description,
        "amount": transaction.amount,
        "category": transaction.category.id,
        "transaction_date": transaction.transaction_date,
        "observation": transaction.observation,
        "student": transaction.student.id if transaction.student else None,
        "professor": transaction.professor.id if transaction.professor else None,
    }
    return JsonResponse(data)


@admin_required
def despesa_list_view(request):
    unidade_ativa_id = request.session.get("unidade_ativa_id")
    if not unidade_ativa_id:
        messages.warning(request, "Selecione uma Unidade de Negócio.")
        return redirect("scheduler:dashboard")

    # 1. Capturar parâmetros de filtro do GET
    descricao = request.GET.get('descricao', '')
    data_inicial = request.GET.get('data_inicial', '')
    data_final = request.GET.get('data_final', '')
    professor_id = request.GET.get('professor', '')
    categoria_id = request.GET.get('categoria', '')
    status = request.GET.get('status', '')

    despesas_list = (
        Despesa.objects.filter(unidade_negocio_id=unidade_ativa_id)
        .select_related("categoria", "professor")
    )

    # 2. Aplicar filtros na queryset
    if descricao:
        despesas_list = despesas_list.filter(descricao__icontains=descricao)
    if data_inicial:
        despesas_list = despesas_list.filter(data_competencia__gte=data_inicial)
    if data_final:
        despesas_list = despesas_list.filter(data_competencia__lte=data_final)
    if professor_id:
        despesas_list = despesas_list.filter(professor_id=professor_id)
    if categoria_id:
        despesas_list = despesas_list.filter(categoria_id=categoria_id)
    if status:
        despesas_list = despesas_list.filter(status=status)

    # Ordenação padrão
    despesas_list = despesas_list.order_by("-data_competencia")

    titulo = "Contas a Pagar"

    filtro_ativo = request.GET.get("filtro")
    if filtro_ativo == "a_vencer":
        hoje = now().date()
        data_limite = hoje + timedelta(days=5)
        despesas_list = despesas_list.filter(
            status="a_pagar",
            data_competencia__gte=hoje,
            data_competencia__lte=data_limite,
        ).order_by("data_competencia")
        titulo = "Despesas a Vencer"

    # --- LÓGICA DE PAGINAÇÃO INSERIDA ---
    paginator = Paginator(despesas_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    # --- FIM DA LÓGICA DE PAGINAÇÃO ---

    if request.method == "POST":
        form = DespesaForm(request.POST)
        if form.is_valid():
            despesa = form.save(commit=False)
            despesa.unidade_negocio_id = unidade_ativa_id

            if despesa.data_pagamento:
                despesa.status = "pago"
                transacao = Transaction.objects.create(
                    unidade_negocio_id=unidade_ativa_id,
                    description=f"Pagamento: {despesa.descricao}",
                    amount=despesa.valor,
                    category=despesa.categoria,
                    transaction_date=despesa.data_pagamento,
                    professor=despesa.professor,
                    created_by=request.user,
                )
                despesa.transacao = transacao

            despesa.save()
            messages.success(request, "Despesa registrada com sucesso!")
            return redirect("finances:despesa_list")
    else:
        form = DespesaForm()

    return render(
        request,
        "finances/despesa_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "titulo": titulo,
            "filtro_ativo": filtro_ativo,
            "professores": CustomUser.objects.filter(tipo__in=['admin', 'professor']),
            "categorias": Category.objects.filter(type='expense'),
            "status_choices": Despesa.STATUS_CHOICES,
            "filtros_aplicados": {
                'descricao': descricao,
                'data_inicial': data_inicial,
                'data_final': data_final,
                'professor': professor_id,
                'categoria': categoria_id,
                'status': status,
            }
        },
    )


@admin_required
def baixar_despesa_view(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk)
    if request.method == "POST":
        data_pagamento_str = request.POST.get("data_pagamento")
        juros_multa_str = request.POST.get("juros_multa", "0")

        if data_pagamento_str:
            data_pagamento = date.fromisoformat(data_pagamento_str)
            juros_multa = Decimal(juros_multa_str or 0)

            try:
                with transaction.atomic():
                    # Cria transação principal (sem alterações aqui)
                    transacao_principal = Transaction.objects.create(
                        unidade_negocio=despesa.unidade_negocio,
                        description=f"Pagamento: {despesa.descricao}",
                        amount=despesa.valor,
                        category=despesa.categoria,
                        transaction_date=data_pagamento,
                        professor=despesa.professor,
                        created_by=request.user,
                    )

                    # Atualiza a despesa (sem alterações aqui)
                    despesa.status = "pago"
                    despesa.data_pagamento = data_pagamento
                    despesa.transacao = transacao_principal
                    despesa.save()

                    # Cria transação para juros/multa se houver
                    if juros_multa > 0:
                        # ==============================================================
                        # ALTERADO AQUI: Usamos get_or_create para criar a categoria se ela não existir
                        # ==============================================================
                        categoria_juros, created = Category.objects.get_or_create(
                            name="Juros e Multas Pagas",
                            type="expense",
                            unidade_negocio=despesa.unidade_negocio,
                            defaults={"tipo_dre": "despesa"},
                        )
                        # ==============================================================

                        Transaction.objects.create(
                            unidade_negocio=despesa.unidade_negocio,
                            description=f"Juros/Multa Ref: {despesa.descricao}",
                            amount=juros_multa,
                            category=categoria_juros,
                            transaction_date=data_pagamento,
                            created_by=request.user,
                        )
                        messages.success(
                            request,
                            f"Despesa e juros de R$ {juros_multa} baixados com sucesso!",
                        )
                    else:
                        messages.success(request, "Despesa baixada com sucesso!")

            except Exception as e:
                # O antigo "Category.DoesNotExist" não é mais necessário, pois o get_or_create resolve isso.
                messages.error(request, f"Ocorreu um erro ao baixar a despesa: {e}")

    return redirect("finances:despesa_list")


@admin_required
def delete_despesa_view(request, pk):
    if request.method == "POST":
        despesa = get_object_or_404(Despesa, pk=pk)
        if despesa.transacao:
            despesa.transacao.delete()
        despesa.delete()
        messages.success(request, "Despesa deletada com sucesso!")
    return redirect("finances:despesa_list")


@admin_required
def edit_despesa_view(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk)
    if request.method == "POST":
        form = DespesaForm(request.POST, instance=despesa)
        if form.is_valid():
            try:
                with transaction.atomic():
                    despesa_atualizada = form.save()

                    if despesa_atualizada.transacao:
                        transacao = despesa_atualizada.transacao
                        transacao.description = (
                            f"Pagamento: {despesa_atualizada.descricao}"
                        )
                        transacao.amount = despesa_atualizada.valor
                        transacao.category = despesa_atualizada.categoria
                        transacao.transaction_date = (
                            despesa_atualizada.data_pagamento
                            or transacao.transaction_date
                        )
                        transacao.save()

                return JsonResponse(
                    {"status": "success", "despesa": model_to_dict(despesa_atualizada)}
                )
            except Exception as e:
                return JsonResponse({"status": "error", "errors": str(e)})
        else:
            return JsonResponse({"status": "error", "errors": form.errors})

    # GET: retorna dados para preencher o modal
    data = model_to_dict(despesa)
    return JsonResponse(data)


@admin_required
def receita_list_view(request):
    """
    View principal, agora filtrando por unidade de negócio e usando o decorador correto.
    """
    unidade_ativa_id = request.session.get("unidade_ativa_id")
    if not unidade_ativa_id:
        messages.warning(request, "Selecione uma Unidade de Negócio.")
        return redirect("scheduler:dashboard")
    
    descricao = request.GET.get('descricao', '')
    data_inicial = request.GET.get('data_inicial', '')
    data_final = request.GET.get('data_final', '')
    aluno_id = request.GET.get('aluno', '')
    categoria_id = request.GET.get('categoria', '')
    status = request.GET.get('status', '')

    receitas_list = Receita.objects.filter(unidade_negocio_id=unidade_ativa_id)

    if descricao:
        receitas_list = receitas_list.filter(descricao__icontains=descricao)
    if data_inicial:
        receitas_list = receitas_list.filter(data_competencia__gte=data_inicial)
    if data_final:
        receitas_list = receitas_list.filter(data_competencia__lte=data_final)
    if aluno_id:
        receitas_list = receitas_list.filter(aluno_id=aluno_id)
    if categoria_id:
        receitas_list = receitas_list.filter(categoria_id=categoria_id)
    if status:
        receitas_list = receitas_list.filter(status=status)

    receitas_list = receitas_list.order_by("-data_competencia")
    titulo = "Contas a Receber"

    filtro_ativo = request.GET.get("filtro")
    if filtro_ativo == "a_vencer":
        hoje = now().date()
        data_limite = hoje + timedelta(days=5)
        receitas_list = receitas_list.filter(
            status="a_receber",
            data_competencia__gte=hoje,
            data_competencia__lte=data_limite,
        ).order_by("data_competencia")
        titulo = "Receitas a Vencer"

    # --- LÓGICA DE PAGINAÇÃO INSERIDA ---
    paginator = Paginator(receitas_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    # --- FIM DA LÓGICA DE PAGINAÇÃO ---

    mensalidade_form = MensalidadeReceitaForm()
    venda_form = VendaReceitaForm()

    context = {
        "page_obj": page_obj,  # <<< ALTERADO
        "mensalidade_form": mensalidade_form,
        "venda_form": venda_form,
        "titulo": titulo,
        "filtro_ativo": filtro_ativo,
        "alunos": Aluno.objects.all(),
        "categorias": Category.objects.filter(type='income'),
        "status_choices": Receita.STATUS_CHOICES,
        "filtros_aplicados": {
            'descricao': descricao,
            'data_inicial': data_inicial,
            'data_final': data_final,
            'aluno': aluno_id,
            'categoria': categoria_id,
            'status': status,
        }
    }
    return render(request, "finances/receita_list.html", context)


@admin_required
def baixar_receita_view(request, pk):
    receita = get_object_or_404(Receita, pk=pk)
    if request.method == "POST":
        data_recebimento_str = request.POST.get("data_recebimento")
        if data_recebimento_str:
            data_recebimento = date.fromisoformat(data_recebimento_str)

            try:
                with transaction.atomic():
                    transacao = Transaction.objects.create(
                        unidade_negocio_id=receita.unidade_negocio.id,
                        description=f"Recebimento: {receita.descricao}",
                        amount=receita.valor,
                        category=receita.categoria,
                        transaction_date=data_recebimento,
                        student=receita.aluno,
                        created_by=request.user,
                    )

                    receita.status = "recebido"
                    receita.data_recebimento = data_recebimento
                    receita.transacao = transacao
                    receita.save()

                    messages.success(request, "Receita baixada com sucesso!")

            except Exception as e:
                messages.error(request, f"Ocorreu um erro ao baixar a receita: {e}")

    return redirect("finances:receita_list")


@admin_required
def delete_receita_view(request, pk):
    if request.method == "POST":
        receita = get_object_or_404(Receita, pk=pk)
        if receita.transacao:
            receita.transacao.delete()
        receita.delete()
        messages.success(request, "Receita deletada com sucesso!")
    return redirect("finances:receita_list")


@admin_required
def edit_mensalidade(request, pk):
    """
    Busca dados e salva alterações para uma MENSALIDADE.
    AGORA USANDO A LÓGICA AJAX.
    """
    receita = get_object_or_404(
        Receita, pk=pk, produto__isnull=True
    )

    if request.method == "POST":
        form = MensalidadeReceitaForm(request.POST, instance=receita)
        if form.is_valid():
            form.save()
            # Responde com JSON em caso de sucesso
            return JsonResponse({"status": "success"})
        else:
            # Responde com JSON e os erros do formulário em caso de falha
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)

    # Para GET, continua retornando os dados da receita em JSON para o modal preencher
    data = {
        "aluno": receita.aluno.pk if receita.aluno else None,
        "descricao": receita.descricao,
        "valor": str(receita.valor),
        "categoria": receita.categoria.pk if receita.categoria else None,
        "data_competencia": (
            receita.data_competencia.strftime("%Y-%m-%d")
            if receita.data_competencia
            else ""
        ),
        "data_recebimento": (
            receita.data_recebimento.strftime("%Y-%m-%d")
            if receita.data_recebimento
            else ""
        ),
    }
    return JsonResponse(data)


@admin_required
def edit_venda(request, pk):
    """
    Busca dados e salva alterações para uma VENDA.
    AGORA USANDO A LÓGICA AJAX.
    """
    receita = get_object_or_404(
        Receita, pk=pk, produto__isnull=False
    )

    quantidade_antiga = receita.quantidade
    produto_antigo = receita.produto

    if request.method == "POST":
        form = VendaReceitaForm(request.POST, instance=receita)
        if form.is_valid():
            try:
                with transaction.atomic():
                    venda_atualizada = form.save(commit=False)
                    produto_novo = venda_atualizada.produto
                    quantidade_nova = venda_atualizada.quantidade

                    if produto_antigo == produto_novo:
                        diferenca_estoque = quantidade_antiga - quantidade_nova
                        produto_novo.quantidade_em_estoque += diferenca_estoque
                    else:
                        produto_antigo.quantidade_em_estoque += quantidade_antiga
                        produto_antigo.save()
                        produto_novo.quantidade_em_estoque -= quantidade_nova

                    if produto_novo.quantidade_em_estoque < 0:
                        raise Exception(
                            f"Estoque insuficiente para o produto '{produto_novo.nome}'."
                        )

                    produto_novo.save()
                    venda_atualizada.save()
                    # Responde com JSON em caso de sucesso
                    return JsonResponse({"status": "success"})

            except Exception as e:
                # Responde com JSON em caso de erro na lógica de estoque
                return JsonResponse({"status": "error", "message": str(e)}, status=400)
        else:
            # Responde com JSON e os erros do formulário em caso de falha
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)

    # Para GET, continua retornando os dados em JSON
    data = {
        "produto": receita.produto.pk if receita.produto else None,
        "quantidade": receita.quantidade,
        "descricao": receita.descricao,
        "valor": str(receita.valor),
        "categoria": receita.categoria.pk if receita.categoria else None,
        "aluno": receita.aluno.pk if receita.aluno else None,
        "data_competencia": (
            receita.data_competencia.strftime("%Y-%m-%d")
            if receita.data_competencia
            else ""
        ),
        "data_recebimento": (
            receita.data_recebimento.strftime("%Y-%m-%d")
            if receita.data_recebimento
            else ""
        ),
    }
    return JsonResponse(data)


@admin_required
def recorrencia_list_view(request):
    unidade_ativa_id = request.session.get("unidade_ativa_id")
    if "submit_despesa" in request.POST:
        despesa_form = DespesaRecorrenteForm(request.POST)
        if despesa_form.is_valid():
            recorrente = despesa_form.save(commit=False)
            recorrente.unidade_negocio_id = unidade_ativa_id
            recorrente.save()
            messages.success(request, "Despesa recorrente salva com sucesso!")
            return redirect("finances:recorrencia_list")
    else:
        despesa_form = DespesaRecorrenteForm()

    if "submit_receita" in request.POST:
        receita_form = ReceitaRecorrenteForm(request.POST)
        if receita_form.is_valid():
            recorrente = receita_form.save(commit=False)
            recorrente.unidade_negocio_id = unidade_ativa_id
            recorrente.save()
            messages.success(request, "Receita recorrente salva com sucesso!")
            return redirect("finances:recorrencia_list")
    else:
        receita_form = ReceitaRecorrenteForm()

    despesas_recorrentes = DespesaRecorrente.objects.filter(
        unidade_negocio_id=unidade_ativa_id
    )
    receitas_recorrentes = ReceitaRecorrente.objects.filter(
        unidade_negocio_id=unidade_ativa_id
    )

    context = {
        "despesa_form": despesa_form,
        "receita_form": receita_form,
        "despesas_recorrentes": despesas_recorrentes,
        "receitas_recorrentes": receitas_recorrentes,
    }
    return render(request, "finances/recorrencia_list.html", context)


@admin_required
def delete_despesa_recorrente_view(request, pk):
    if request.method == "POST":
        recorrente = get_object_or_404(DespesaRecorrente, pk=pk)
        recorrente.delete()
        messages.success(request, "Despesa recorrente deletada com sucesso!")
    return redirect("finances:recorrencia_list")


@admin_required
def edit_despesa_recorrente_view(request, pk):
    recorrente = get_object_or_404(DespesaRecorrente, pk=pk)
    if request.method == "POST":
        form = DespesaRecorrenteForm(request.POST, instance=recorrente)
        if form.is_valid():
            form.save()
            return JsonResponse({"status": "success"})
        else:
            return JsonResponse({"status": "error", "errors": form.errors})
    data = model_to_dict(recorrente)
    return JsonResponse(data)


@admin_required
def delete_receita_recorrente_view(request, pk):
    if request.method == "POST":
        recorrente = get_object_or_404(ReceitaRecorrente, pk=pk)
        recorrente.delete()
        messages.success(request, "Receita recorrente deletada com sucesso!")
    return redirect("finances:recorrencia_list")


@admin_required
def edit_receita_recorrente_view(request, pk):
    recorrente = get_object_or_404(ReceitaRecorrente, pk=pk)
    if request.method == "POST":
        form = ReceitaRecorrenteForm(request.POST, instance=recorrente)
        if form.is_valid():
            form.save()
            return JsonResponse({"status": "success"})
        else:
            return JsonResponse({"status": "error", "errors": form.errors})
    data = model_to_dict(recorrente)
    return JsonResponse(data)


def get_dre_data(unidade_negocio_id, start_date, end_date):
    """Busca e calcula os dados para o DRE de um período específico."""
    if not all([unidade_negocio_id, start_date, end_date]):
        return None

    receitas_periodo = Receita.objects.filter(
        unidade_negocio_id=unidade_negocio_id,
        data_competencia__range=[start_date, end_date],
    )
    despesas_periodo = Despesa.objects.filter(
        unidade_negocio_id=unidade_negocio_id,
        data_competencia__range=[start_date, end_date],
    )

    data = {}
    data["receitas_por_categoria"] = list(
        receitas_periodo.values("categoria__name")
        .annotate(total_cat=Sum("valor"))
        .order_by("-total_cat")
    )
    data["total_receitas"] = receitas_periodo.aggregate(total=Sum("valor"))[
        "total"
    ] or Decimal("0.00")

    custos_q = despesas_periodo.filter(categoria__tipo_dre="custo")
    despesas_q = despesas_periodo.filter(categoria__tipo_dre="despesa")

    data["custos_por_categoria"] = list(
        custos_q.values("categoria__name").annotate(total_cat=Sum("valor"))
    )
    data["total_custos"] = custos_q.aggregate(total=Sum("valor"))["total"] or Decimal(
        "0.00"
    )

    data["despesas_por_categoria"] = list(
        despesas_q.values("categoria__name").annotate(total_cat=Sum("valor"))
    )
    data["total_despesas"] = despesas_q.aggregate(total=Sum("valor"))[
        "total"
    ] or Decimal("0.00")

    data["lucro_bruto"] = data["total_receitas"] - data["total_custos"]
    data["resultado"] = data["lucro_bruto"] - data["total_despesas"]

    if data["total_receitas"] > 0:
        data["perc_custos"] = data["total_custos"] / data["total_receitas"] * 100
        data["perc_lucro_bruto"] = data["lucro_bruto"] / data["total_receitas"] * 100
        data["perc_despesas"] = data["total_despesas"] / data["total_receitas"] * 100
        data["perc_resultado"] = data["resultado"] / data["total_receitas"] * 100
    else:
        data["perc_custos"] = data["perc_lucro_bruto"] = data["perc_despesas"] = data[
            "perc_resultado"
        ] = Decimal("0.00")

    return data


def merge_and_compare_categories(principal_list, comp_list):
    """
    Combina e compara duas listas de categorias, calculando a variação para cada item.
    """
    comp_dict = {item["categoria__name"]: item["total_cat"] for item in comp_list}
    principal_dict = {
        item["categoria__name"]: item["total_cat"] for item in principal_list
    }

    all_category_names = sorted(
        list(set(principal_dict.keys()) | set(comp_dict.keys()))
    )

    merged_list = []
    for name in all_category_names:
        principal_val = principal_dict.get(name, Decimal("0.00"))
        comp_val = comp_dict.get(name, Decimal("0.00"))

        var_abs = principal_val - comp_val
        if comp_val != 0:
            var_perc = var_abs / comp_val * 100
        elif principal_val != 0:
            var_perc = Decimal("100.0")
        else:
            var_perc = Decimal("0.0")

        merged_list.append(
            {
                "name": name,
                "principal": principal_val,
                "comparativo": comp_val,
                "var_abs": var_abs,
                "var_perc": var_perc,
            }
        )
    return merged_list


@admin_required
def dre_view(request):
    unidade_ativa_id = request.session.get("unidade_ativa_id")
    if not unidade_ativa_id:
        messages.warning(request, "Selecione uma Unidade de Negócio.")
        return redirect("scheduler:dashboard")

    today = now().date()

    # Período Principal
    start_date = (
        date.fromisoformat(request.GET.get("start_date"))
        if request.GET.get("start_date")
        else today.replace(day=1)
    )
    end_date = (
        date.fromisoformat(request.GET.get("end_date"))
        if request.GET.get("end_date")
        else (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        - timedelta(days=1)
    )

    # Período Comparativo
    start_date_comp_str = request.GET.get("start_date_comp")
    end_date_comp_str = request.GET.get("end_date_comp")
    start_date_comp = (
        date.fromisoformat(start_date_comp_str) if start_date_comp_str else None
    )
    end_date_comp = date.fromisoformat(end_date_comp_str) if end_date_comp_str else None

    dre_principal = get_dre_data(unidade_ativa_id, start_date, end_date)
    dre_comp = (
        get_dre_data(unidade_ativa_id, start_date_comp, end_date_comp)
        if start_date_comp and end_date_comp
        else None
    )

    context = {
        "start_date": start_date,
        "end_date": end_date,
        "start_date_comp": start_date_comp,
        "end_date_comp": end_date_comp,
        "dre_principal": dre_principal,
        "dre_comp": dre_comp,
        "kpis": [
            {"kpi": "receita", "label": "Receita Bruta", "color": "success"},
            {"kpi": "custos", "label": "Custos Diretos", "color": "danger"},
            {"kpi": "lucro", "label": "Lucro Bruto", "color": "dark"},
            {"kpi": "resultado", "label": "Resultado", "color": "info"},
        ],
    }

    # Se houver comparação, calcula as variações
    if dre_comp:
        variacoes = {}
        for key in [
            "total_receitas",
            "total_custos",
            "lucro_bruto",
            "total_despesas",
            "resultado",
        ]:
            val_principal = dre_principal.get(key, Decimal("0.00"))
            val_comp = dre_comp.get(key, Decimal("0.00"))

            var_abs = val_principal - val_comp
            var_perc = (var_abs / val_comp * 100) if val_comp != 0 else Decimal("0.00")
            variacoes[key] = {"abs": var_abs, "perc": var_perc}
        context["variacoes"] = variacoes

    return render(request, "finances/dre_report.html", context)


@admin_required
def dre_details_view(request):
    unidade_ativa_id = request.session.get("unidade_ativa_id")

    category_name = request.GET.get("categoria")
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    modelo = request.GET.get("modelo")

    if not all([unidade_ativa_id, category_name, start_date_str, end_date_str, modelo]):
        messages.error(request, "Parâmetros insuficientes para gerar o detalhamento.")
        return redirect("finances:dre_report")

    try:
        start_date_obj = date.fromisoformat(start_date_str)
        end_date_obj = date.fromisoformat(end_date_str)
    except (ValueError, TypeError):
        messages.error(request, "Formato de data inválido.")
        return redirect("finances:dre_report")

    lancamentos = []
    total_categoria = Decimal("0.00")

    if modelo == "receita":
        qs = Receita.objects.filter(
            unidade_negocio_id=unidade_ativa_id,
            categoria__name=category_name,
            data_competencia__range=[start_date_obj, end_date_obj],
        )
        total_categoria = qs.aggregate(total=Sum("valor"))["total"] or Decimal("0.00")
        lancamentos = qs.order_by("-data_competencia")

    elif modelo == "despesa":
        classificacao = request.GET.get("classificacao")
        qs = Despesa.objects.filter(
            unidade_negocio_id=unidade_ativa_id,
            categoria__name=category_name,
            data_competencia__range=[start_date_obj, end_date_obj],
            categoria__tipo_dre=classificacao,
        )
        total_categoria = qs.aggregate(total=Sum("valor"))["total"] or Decimal("0.00")
        lancamentos = qs.order_by("-data_competencia")

    context = {
        "lancamentos": lancamentos,
        "category_name": category_name,
        "start_date": start_date_obj,
        "end_date": end_date_obj,
        "modelo": modelo,
        "total_categoria": total_categoria,
    }
    return render(request, "finances/dre_details.html", context)


# Em finances/views.py

@admin_required
def export_dre_xlsx(request):
    unidade_ativa_id = request.session.get("unidade_ativa_id")
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    start_date_comp_str = request.GET.get("start_date_comp")
    end_date_comp_str = request.GET.get("end_date_comp")

    start_date = date.fromisoformat(start_date_str)
    end_date = date.fromisoformat(end_date_str)
    dre_data = get_dre_data(unidade_ativa_id, start_date, end_date)
    dre_comp = None
    if start_date_comp_str and end_date_comp_str:
        start_date_comp = date.fromisoformat(start_date_comp_str)
        end_date_comp = date.fromisoformat(end_date_comp_str)
        dre_comp = get_dre_data(unidade_ativa_id, start_date_comp, end_date_comp)

    wb = Workbook()
    ws = wb.active
    ws.title = "DRE"

    bold_font = Font(bold=True)
    green_font = Font(color="008000")
    red_font = Font(color="FF0000")
    total_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    final_total_fill = PatternFill(start_color="AFAFAF", end_color="343A40", fill_type="solid")
    final_total_font = Font(bold=True, color="FFFFFF")
    right_align = Alignment(horizontal="right")
    center_align = Alignment(horizontal="center")
    thin_side = Side(style='thin')

    headers = ['Descrição', 'Período Principal']
    if dre_comp:
        headers.extend(['Período Comparativo', 'Variação (R$)', 'Variação (%)'])
    num_cols = len(headers)
    
    ws['A1'] = 'Demonstrativo de Resultados (DRE)'
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    ws['A1'].font = Font(bold=True, size=16)
    ws['A1'].alignment = center_align

    # ==============================================================================
    # --- LÓGICA DA LINHA DE PERÍODO (SIMPLIFICADA E CORRIGIDA) ---
    # ==============================================================================
    periodo_str = f'Principal: {start_date.strftime("%d/%m/%Y")} a {end_date.strftime("%d/%m/%Y")}'
    if dre_comp:
        periodo_str += f' | Comparativo: {start_date_comp.strftime("%d/%m/%Y")} a {end_date_comp.strftime("%d/%m/%Y")}'
    
    ws['A2'] = periodo_str # Atribuição de texto simples
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
    ws['A2'].alignment = center_align
    # ws['A2'].font = bold_font # Opcional: descomente esta linha se quiser a linha toda em negrito
    # ==============================================================================

    for col_idx, header_title in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx)
        cell.value = header_title.upper()
        cell.font = bold_font
        cell.fill = total_fill
        cell.alignment = center_align if col_idx > 1 else None

    if dre_comp:
        # Lógica de comparação (sem alterações)
        variacoes = {}
        for key in ['total_receitas', 'total_custos', 'lucro_bruto', 'total_despesas', 'resultado']:
            val_principal = dre_data.get(key, Decimal('0.00'))
            val_comp = dre_comp.get(key, Decimal('0.00'))
            var_abs = val_principal - val_comp
            var_perc = (var_abs / val_comp * 100) if val_comp != 0 else Decimal('0.00')
            variacoes[key] = {'abs': var_abs, 'perc': var_perc}
        
        receitas_detalhadas = merge_and_compare_categories(dre_data.get('receitas_por_categoria', []), dre_comp.get('receitas_por_categoria', []))
        custos_detalhados = merge_and_compare_categories(dre_data.get('custos_por_categoria', []), dre_comp.get('custos_por_categoria', []))
        despesas_detalhadas = merge_and_compare_categories(dre_data.get('despesas_por_categoria', []), dre_comp.get('despesas_por_categoria', []))

        ws.append(['(+) Receita Operacional Bruta', dre_data['total_receitas'], dre_comp['total_receitas'], variacoes['total_receitas']['abs'], variacoes['total_receitas']['perc']])
        for r in receitas_detalhadas: ws.append([f"  + {r['name']}", r['principal'], r['comparativo'], r['var_abs'], r['var_perc']])
        ws.append(['(-) Custos Diretos', -dre_data['total_custos'], -dre_comp['total_custos'], -variacoes['total_custos']['abs'], -variacoes['total_custos']['perc']])
        for c in custos_detalhados: ws.append([f"  - {c['name']}", -c['principal'], -c['comparativo'], -c['var_abs'], -c['var_perc']])
        ws.append(['(=) Lucro Bruto', dre_data['lucro_bruto'], dre_comp['lucro_bruto'], variacoes['lucro_bruto']['abs'], variacoes['lucro_bruto']['perc']])
        ws.append(['(-) Despesas Operacionais', -dre_data['total_despesas'], -dre_comp['total_despesas'], -variacoes['total_despesas']['abs'], -variacoes['total_despesas']['perc']])
        for d in despesas_detalhadas: ws.append([f"  - {d['name']}", -d['principal'], -d['comparativo'], -d['var_abs'], -d['var_perc']])
        ws.append(['(=) RESULTADO DO PERÍODO', dre_data['resultado'], dre_comp['resultado'], variacoes['resultado']['abs'], variacoes['resultado']['perc']])
    else:
        # Lógica de período único (sem alterações)
        ws.append(['(+) Receita Operacional Bruta', dre_data['total_receitas']])
        for r in dre_data['receitas_por_categoria']: ws.append([f"  + {r['categoria__name']}", r['total_cat']])
        ws.append(['(-) Custos Diretos', -dre_data['total_custos']])
        for c in dre_data['custos_por_categoria']: ws.append([f"  - {c['categoria__name']}", -c['total_cat']])
        ws.append(['(=) Lucro Bruto', dre_data['lucro_bruto']])
        ws.append(['(-) Despesas Operacionais', -dre_data['total_despesas']])
        for d in dre_data['despesas_por_categoria']: ws.append([f"  - {d['categoria__name']}", -d['total_cat']])
        ws.append(['(=) RESULTADO DO PERÍODO', dre_data['resultado']])

    for row_idx, row in enumerate(ws.iter_rows(min_row=5), start=5):
        desc_cell = row[0]
        desc_val = desc_cell.value.strip() if desc_cell.value else ""
        is_total_row = desc_val.startswith(('(+)', '(-)', '(=)'))
        is_final_row = 'RESULTADO' in desc_val
        if is_final_row:
            for cell in row: cell.fill = final_total_fill; cell.font = final_total_font
        elif is_total_row:
            for cell in row: cell.fill = total_fill; cell.font = bold_font
        for col_idx, cell in enumerate(row[1:], start=2):
            cell.alignment = right_align
            if not isinstance(cell.value, (int, float, Decimal)): continue
            is_bold = cell.font.bold
            color_rgb = None
            if col_idx <= 3:
                if desc_val.startswith(('(+) Receita', '(=) Lucro', '(=) RESULTADO')):
                    color_rgb = green_font.color.rgb if cell.value >= 0 else red_font.color.rgb
                elif desc_val.startswith(('(-) Custos', '(-) Despesas')):
                    color_rgb = red_font.color.rgb
            elif col_idx >= 4 and dre_comp:
                is_good_variation = False
                if desc_val.startswith(('(+) Receita', '(=) Lucro', '(=) RESULTADO')):
                    is_good_variation = cell.value >= 0
                elif desc_val.startswith(('(-) Custos', '(-) Despesas')):
                    is_good_variation = cell.value <= 0
                color_rgb = green_font.color.rgb if is_good_variation else red_font.color.rgb
            if color_rgb:
                cell.font = Font(bold=is_bold, color=color_rgb)

    min_row = 4
    max_row = ws.max_row
    min_col = 1
    max_col = len(headers)

    for row in ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
        for cell in row:
            border = Border()
            if cell.column == min_col:
                border.left = thin_side
            if cell.column == max_col:
                border.right = thin_side
            if cell.row == min_row:
                border.top = thin_side
            if cell.row == max_row:
                border.bottom = thin_side
            cell.border = border

    ws.column_dimensions['A'].width = 50
    for col in ws.iter_cols(min_col=2, max_col=ws.max_column):
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = 22
        for cell in col:
            if isinstance(cell.value, (int, float, Decimal)):
                if col_letter == 'E':
                    cell.number_format = '0.0"%"'
                else:
                    cell.number_format = 'R$ #,##0.00;[Red]-R$ #,##0.00'

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    file_name = f'DRE_{start_date_str}_a_{end_date_str}.xlsx'
    if dre_comp:
        file_name = f'DRE_Comparativo_{start_date_str}_vs_{start_date_comp_str}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    wb.save(response)
    return response

@admin_required
def export_dre_pdf(request):
    unidade_ativa_id = request.session.get("unidade_ativa_id")
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    # --- LÓGICA DE COMPARAÇÃO ADICIONADA ---
    start_date_comp_str = request.GET.get("start_date_comp")
    end_date_comp_str = request.GET.get("end_date_comp")

    start_date = date.fromisoformat(start_date_str)
    end_date = date.fromisoformat(end_date_str)
    start_date_comp = (
        date.fromisoformat(start_date_comp_str) if start_date_comp_str else None
    )
    end_date_comp = date.fromisoformat(end_date_comp_str) if end_date_comp_str else None

    dre_data = get_dre_data(unidade_ativa_id, start_date, end_date)
    dre_comp = (
        get_dre_data(unidade_ativa_id, start_date_comp, end_date_comp)
        if start_date_comp and end_date_comp
        else None
    )

    context = {
        "dre_data": dre_data,
        "start_date": start_date,
        "end_date": end_date,
        "dre_comp": dre_comp,  # Passa os dados do comparativo
    }

    # Calcula as variações se houver um período comparativo
    if dre_comp:
        variacoes = {}
        for key in [
            "total_receitas",
            "total_custos",
            "lucro_bruto",
            "total_despesas",
            "resultado",
        ]:
            val_principal = dre_data.get(key, Decimal("0.00"))
            val_comp = dre_comp.get(key, Decimal("0.00"))
            var_abs = val_principal - val_comp
            var_perc = (var_abs / val_comp * 100) if val_comp != 0 else Decimal("0.00")
            variacoes[key] = {"abs": var_abs, "perc": var_perc}
        context["variacoes"] = variacoes  # Passa as variações

    # --- FIM DA LÓGICA ADICIONADA ---

    html_string = render_to_string("finances/dre_pdf_template.html", context)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="DRE_{start_date_str}_a_{end_date_str}.pdf"'
    )

    # Usando xhtml2pdf que parece ser a biblioteca que você tem
    pisa_status = pisa.CreatePDF(html_string, dest=response)
    if pisa_status.err:
        return HttpResponse("Tivemos alguns erros <pre>" + html_string + "</pre>")
    return response


@login_required
def get_aluno_details(request, aluno_id):
    """
    Retorna JSON com detalhes do aluno para preenchimento automático
    no formulário de Contas a Receber.
    """
    try:
        aluno = get_object_or_404(Aluno, pk=aluno_id)
        status_pagamento = aluno.get_status_pagamento()
        data = {
            "id": aluno.id,
            "nome_completo": aluno.nome_completo,
            "valor_mensalidade": float(aluno.valor_mensalidade or 0),
            "dia_vencimento": aluno.dia_vencimento or "",
            "status": status_pagamento["status"],
            "status_cor": status_pagamento["cor"],
            "email": aluno.email or "",
            "telefone": aluno.telefone or "",
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@admin_required
@require_POST
def toggle_recorrencia_ativa(request):
    try:
        model_name = request.POST.get("model")
        pk = request.POST.get("pk")
        is_active = request.POST.get("is_active") == "true"

        Model = apps.get_model("finances", model_name)
        recorrencia = get_object_or_404(Model, pk=pk)

        recorrencia.ativa = is_active
        recorrencia.save()

        return JsonResponse(
            {"status": "success", "message": f"{model_name} atualizada."}
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@admin_required
def calcular_pagamento_professor_ajax(request):
    professor_id = request.GET.get("professor_id")
    data_inicial_str = request.GET.get("data_inicial")
    data_final_str = request.GET.get("data_final")

    if not all([professor_id, data_inicial_str, data_final_str]):
        return JsonResponse(
            {"status": "error", "message": "Parâmetros ausentes."}, status=400
        )

    try:
        professor = get_object_or_404(CustomUser, pk=professor_id)
        data_inicial = datetime.strptime(data_inicial_str, "%Y-%m-%d").date()
        data_final = datetime.strptime(data_final_str, "%Y-%m-%d").date()
    except (ValueError, CustomUser.DoesNotExist):
        return JsonResponse(
            {"status": "error", "message": "Parâmetros inválidos."}, status=400
        )

    # 1. Filtra aulas realizadas
    q_realizadas_normal = Q(
        status="Realizada", relatorioaula__professor_que_validou=professor
    ) & ~Q(modalidade__nome__icontains="atividade complementar")
    q_realizadas_ac = Q(
        status="Realizada",
        modalidade__nome__icontains="atividade complementar",
        presencas_professores__professor=professor,
        presencas_professores__status="presente",
    )

    aulas_realizadas = (
        Aula.objects.filter(
            data_hora__date__gte=data_inicial, data_hora__date__lte=data_final
        )
        .filter(q_realizadas_normal | q_realizadas_ac)
        .distinct()
    )

    # 2. Agrupa por modalidade
    calculo_detalhado = []
    modalidades_envolvidas = Modalidade.objects.filter(
        aula__in=aulas_realizadas
    ).distinct()

    for modalidade in modalidades_envolvidas:
        aulas_nesta_modalidade = aulas_realizadas.filter(modalidade=modalidade)

        item_calculo = {
            "modalidade_nome": modalidade.nome,
            "tipo_pagamento_display": modalidade.get_tipo_pagamento_display(),
            "valor_unitario": float(modalidade.valor_pagamento_professor),
        }

        # 3. Aplica a regra
        if modalidade.tipo_pagamento == "aluno":
            quantidade = PresencaAluno.objects.filter(
                aula__in=aulas_nesta_modalidade, status="presente"
            ).count()
            item_calculo["unidade_contagem"] = "aluno(s) presente(s)"
        else:
            quantidade = aulas_nesta_modalidade.count()
            item_calculo["unidade_contagem"] = "aula(s)"

        item_calculo["quantidade"] = quantidade
        item_calculo["subtotal"] = float(
            Decimal(quantidade) * modalidade.valor_pagamento_professor
        )

        if quantidade > 0:
            calculo_detalhado.append(item_calculo)

    return JsonResponse(
        {
            "status": "success",
            "professor_name": professor.get_full_name() or professor.username,
            "calculo": calculo_detalhado,
        }
    )
