from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Transaction, Despesa, Receita, DespesaRecorrente, ReceitaRecorrente, Category
from .forms import TransactionForm, CategoryForm, DespesaForm, ReceitaForm, DespesaRecorrenteForm, ReceitaRecorrenteForm
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.forms.models import model_to_dict
from django.db.models import Sum
from django.db import transaction
from django.core.paginator import Paginator
from datetime import date, timedelta
from django.utils.timezone import now
from functools import wraps
from django.contrib.auth.decorators import login_required
from store.models import Produto


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
    day = min(start_date.day, [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month])
    return date(year, month, day)


@admin_required
def transaction_list_view(request):
    MESES_PT = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
        5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
    }
    unidade_ativa_id = request.session.get('unidade_ativa_id')
    if not unidade_ativa_id:
        messages.warning(request, "Selecione uma Unidade de Negócio.")
        return redirect('scheduler:dashboard')

    today = now().date()
    start_date = date.fromisoformat(request.GET.get('start_date')) if request.GET.get('start_date') else today.replace(day=1)
    end_date = date.fromisoformat(request.GET.get('end_date')) if request.GET.get('end_date') else (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    total_a_pagar = Despesa.objects.filter(
        unidade_negocio_id=unidade_ativa_id,
        status='a_pagar',
        data_competencia__range=[start_date, end_date]
    ).aggregate(total=Sum('valor'))['total'] or 0

    total_a_receber = Receita.objects.filter(
        unidade_negocio_id=unidade_ativa_id,
        status='a_receber',
        data_competencia__range=[start_date, end_date]
    ).aggregate(total=Sum('valor'))['total'] or 0

    transactions = Transaction.objects.filter(
        unidade_negocio_id=unidade_ativa_id,
        transaction_date__range=[start_date, end_date]
    ).select_related('category')

    total_income = transactions.filter(category__type='income').aggregate(total=Sum('amount'))['total'] or 0
    total_expenses = transactions.filter(category__type='expense').aggregate(total=Sum('amount'))['total'] or 0
    balance = total_income - total_expenses

    expenses_by_category = transactions.filter(category__type='expense') \
        .values('category__name') \
        .annotate(total=Sum('amount')) \
        .order_by('-total')

    chart_labels = [item['category__name'] for item in expenses_by_category]
    chart_data = [float(item['total']) for item in expenses_by_category]

    months_spanned = max(1, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1)
    avg_monthly_income = Decimal(total_income) / months_spanned
    avg_monthly_expenses = Decimal(total_expenses) / months_spanned
    cumulative_balance = balance
    monthly_net = avg_monthly_income - avg_monthly_expenses

    projection_data = []
    for i in range(1, 7):
        future_date = add_months(end_date.replace(day=1), i)
        cumulative_balance += monthly_net
        projection_data.append({
            'month': f"{MESES_PT[future_date.month]}/{future_date.year}",
            'income': avg_monthly_income,
            'expenses': avg_monthly_expenses,
            'balance': cumulative_balance,
        })

    paginator = Paginator(transactions, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    form = TransactionForm(initial={'unidade_negocio': unidade_ativa_id})
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            t = form.save(commit=False)
            t.created_by = request.user
            t.unidade_negocio_id = unidade_ativa_id
            t.save()
            messages.success(request, "Lançamento adicionado com sucesso!")
            return redirect(request.get_full_path())

    return render(request, 'finances/transaction_list.html', {
        'page_obj': page_obj,
        'form': form,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': balance,
        'start_date': start_date,
        'end_date': end_date,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'projection_data': projection_data,
        'total_a_pagar': total_a_pagar,
        'total_a_receber': total_a_receber,
    })


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
def delete_transaction_view(request, pk):
    if request.method == "POST":
        transaction = get_object_or_404(Transaction, pk=pk)
        transaction.delete()
        messages.success(request, "Lançamento deletado com sucesso!")
    return redirect("finances:transaction_list")


@admin_required
def edit_transaction_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            updated_transaction = form.save()

            data = model_to_dict(updated_transaction)
            data['category_name'] = updated_transaction.category.name
            data['student_name'] = updated_transaction.student.nome_completo if updated_transaction.student else ""
            data['professor_name'] = updated_transaction.professor.username if updated_transaction.professor else ""

            return JsonResponse({'status': 'success', 'transaction': data})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})

    data = {
        'id': transaction.id,
        'description': transaction.description,
        'amount': transaction.amount,
        'category': transaction.category.id,
        'transaction_date': transaction.transaction_date,
        'observation': transaction.observation,
        'student': transaction.student.id if transaction.student else None,
        'professor': transaction.professor.id if transaction.professor else None,
    }
    return JsonResponse(data)


@admin_required
def despesa_list_view(request):
    unidade_ativa_id = request.session.get('unidade_ativa_id')
    if not unidade_ativa_id:
        messages.warning(request, "Selecione uma Unidade de Negócio.")
        return redirect('scheduler:dashboard')

    despesas = Despesa.objects.filter(unidade_negocio_id=unidade_ativa_id).select_related('categoria', 'professor').order_by('-data_competencia')

    if request.method == 'POST':
        form = DespesaForm(request.POST)
        if form.is_valid():
            despesa = form.save(commit=False)
            despesa.unidade_negocio_id = unidade_ativa_id

            if despesa.data_pagamento:
                despesa.status = 'pago'
                transacao = Transaction.objects.create(
                    unidade_negocio_id=unidade_ativa_id,
                    description=f"Pagamento: {despesa.descricao}",
                    amount=despesa.valor,
                    category=despesa.categoria,
                    transaction_date=despesa.data_pagamento,
                    professor=despesa.professor,
                    created_by=request.user
                )
                despesa.transacao = transacao

            despesa.save()
            messages.success(request, 'Despesa registrada com sucesso!')
            return redirect('finances:despesa_list')
    else:
        form = DespesaForm()

    return render(request, 'finances/despesa_list.html', {
        'form': form,
        'despesas': despesas
    })


@admin_required
def baixar_despesa_view(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk)
    if request.method == 'POST':
        data_pagamento_str = request.POST.get('data_pagamento')
        juros_multa_str = request.POST.get('juros_multa', '0')

        if data_pagamento_str:
            data_pagamento = date.fromisoformat(data_pagamento_str)
            juros_multa = Decimal(juros_multa_str or 0)

            try:
                with transaction.atomic():
                    # Cria transação principal
                    transacao_principal = Transaction.objects.create(
                        unidade_negocio_id=despesa.unidade_negocio.id,
                        description=f"Pagamento: {despesa.descricao}",
                        amount=despesa.valor,
                        category=despesa.categoria,
                        transaction_date=data_pagamento,
                        professor=despesa.professor,
                        created_by=request.user
                    )

                    # Atualiza a despesa
                    despesa.status = 'pago'
                    despesa.data_pagamento = data_pagamento
                    despesa.transacao = transacao_principal
                    despesa.save()

                    # Cria transação para juros/multa se houver
                    if juros_multa > 0:
                        categoria_juros = Category.objects.get(name__iexact="Juros e Multas Pagas", type="expense")
                        Transaction.objects.create(
                            unidade_negocio_id=despesa.unidade_negocio.id,
                            description=f"Juros/Multa Ref: {despesa.descricao}",
                            amount=juros_multa,
                            category=categoria_juros,
                            transaction_date=data_pagamento,
                            created_by=request.user
                        )
                        messages.success(request, f'Despesa e juros de R$ {juros_multa} baixados com sucesso!')
                    else:
                        messages.success(request, 'Despesa baixada com sucesso!')

            except Category.DoesNotExist:
                messages.error(request, 'Categoria "Juros e Multas Pagas" não encontrada. Juros não registrados.')
            except Exception as e:
                messages.error(request, f"Ocorreu um erro ao baixar a despesa: {e}")

    return redirect('finances:despesa_list')


@admin_required
def delete_despesa_view(request, pk):
    if request.method == 'POST':
        despesa = get_object_or_404(Despesa, pk=pk)
        if despesa.transacao:
            despesa.transacao.delete()
        despesa.delete()
        messages.success(request, 'Despesa deletada com sucesso!')
    return redirect('finances:despesa_list')


@admin_required
def edit_despesa_view(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk)
    if request.method == 'POST':
        form = DespesaForm(request.POST, instance=despesa)
        if form.is_valid():
            try:
                with transaction.atomic():
                    despesa_atualizada = form.save()

                    if despesa_atualizada.transacao:
                        transacao = despesa_atualizada.transacao
                        transacao.description = f"Pagamento: {despesa_atualizada.descricao}"
                        transacao.amount = despesa_atualizada.valor
                        transacao.category = despesa_atualizada.categoria
                        transacao.transaction_date = despesa_atualizada.data_pagamento or transacao.transaction_date
                        transacao.save()

                return JsonResponse({'status': 'success', 'despesa': model_to_dict(despesa_atualizada)})
            except Exception as e:
                return JsonResponse({'status': 'error', 'errors': str(e)})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})

    # GET: retorna dados para preencher o modal
    data = model_to_dict(despesa)
    return JsonResponse(data)


@admin_required
def receita_list_view(request):
    unidade_ativa_id = request.session.get('unidade_ativa_id')
    if not unidade_ativa_id:
        messages.warning(request, "Selecione uma Unidade de Negócio.")
        return redirect('scheduler:dashboard')

    receitas = Receita.objects.filter(unidade_negocio_id=unidade_ativa_id).select_related('categoria', 'aluno', 'produto').order_by('-data_competencia')

    if request.method == 'POST':
        form = ReceitaForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    receita = form.save(commit=False)
                    receita.unidade_negocio_id = unidade_ativa_id

                    produto_vendido = form.cleaned_data.get('produto')
                    quantidade_vendida = form.cleaned_data.get('quantidade')

                    if produto_vendido and quantidade_vendida:
                        produto = Produto.objects.select_for_update().get(pk=produto_vendido.pk)
                        if produto.quantidade_em_estoque < quantidade_vendida:
                            messages.error(request, f"Estoque insuficiente para '{produto.nome}'. Disponível: {produto.quantidade_em_estoque}")
                            return redirect('finances:receita_list')
                        produto.quantidade_em_estoque -= quantidade_vendida
                        produto.save()

                    if receita.data_recebimento:
                        receita.status = 'recebido'
                        transacao = Transaction.objects.create(
                            unidade_negocio_id=unidade_ativa_id,
                            description=f"Recebimento: {receita.descricao}",
                            amount=receita.valor,
                            category=receita.categoria,
                            transaction_date=receita.data_recebimento,
                            student=receita.aluno,
                            created_by=request.user
                        )
                        receita.transacao = transacao

                    receita.save()
                    messages.success(request, 'Venda registrada com sucesso!')

            except Exception as e:
                messages.error(request, f"Ocorreu um erro ao processar a venda: {e}")

            return redirect('finances:receita_list')
    else:
        form = ReceitaForm()

    return render(request, 'finances/receita_list.html', {
        'form': form,
        'receitas': receitas
    })


@admin_required
def baixar_receita_view(request, pk):
    receita = get_object_or_404(Receita, pk=pk)
    if request.method == 'POST':
        data_recebimento_str = request.POST.get('data_recebimento')
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
                        created_by=request.user
                    )

                    receita.status = 'recebido'
                    receita.data_recebimento = data_recebimento
                    receita.transacao = transacao
                    receita.save()

                    messages.success(request, 'Receita baixada com sucesso!')

            except Exception as e:
                messages.error(request, f"Ocorreu um erro ao baixar a receita: {e}")

    return redirect('finances:receita_list')


@admin_required
def delete_receita_view(request, pk):
    if request.method == 'POST':
        receita = get_object_or_404(Receita, pk=pk)
        if receita.transacao:
            receita.transacao.delete()
        receita.delete()
        messages.success(request, 'Receita deletada com sucesso!')
    return redirect('finances:receita_list')


@admin_required
def edit_receita_view(request, pk):
    receita = get_object_or_404(Receita, pk=pk)
    if request.method == 'POST':
        form = ReceitaForm(request.POST, instance=receita)
        if form.is_valid():
            try:
                with transaction.atomic():
                    receita_atualizada = form.save()

                    if receita_atualizada.transacao:
                        transacao = receita_atualizada.transacao
                        transacao.description = f"Recebimento: {receita_atualizada.descricao}"
                        transacao.amount = receita_atualizada.valor
                        transacao.category = receita_atualizada.categoria
                        transacao.transaction_date = receita_atualizada.data_recebimento or transacao.transaction_date
                        transacao.student = receita_atualizada.aluno
                        transacao.save()

                return JsonResponse({'status': 'success', 'receita': model_to_dict(receita_atualizada)})
            except Exception as e:
                return JsonResponse({'status': 'error', 'errors': str(e)})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})

    data = model_to_dict(receita)
    data['categoria'] = receita.categoria.id if receita.categoria else None
    data['aluno'] = receita.aluno.id if receita.aluno else None
    data['produto'] = receita.produto.id if receita.produto else None
    data['quantidade'] = receita.quantidade if receita.quantidade else 1
    return JsonResponse(data)


@admin_required
def recorrencia_list_view(request):
    unidade_ativa_id = request.session.get('unidade_ativa_id')
    if 'submit_despesa' in request.POST:
        despesa_form = DespesaRecorrenteForm(request.POST)
        if despesa_form.is_valid():
            recorrente = despesa_form.save(commit=False)
            recorrente.unidade_negocio_id = unidade_ativa_id
            recorrente.save()
            messages.success(request, 'Despesa recorrente salva com sucesso!')
            return redirect('finances:recorrencia_list')
    else:
        despesa_form = DespesaRecorrenteForm()

    if 'submit_receita' in request.POST:
        receita_form = ReceitaRecorrenteForm(request.POST)
        if receita_form.is_valid():
            recorrente = receita_form.save(commit=False)
            recorrente.unidade_negocio_id = unidade_ativa_id
            recorrente.save()
            messages.success(request, 'Receita recorrente salva com sucesso!')
            return redirect('finances:recorrencia_list')
    else:
        receita_form = ReceitaRecorrenteForm()

    despesas_recorrentes = DespesaRecorrente.objects.filter(unidade_negocio_id=unidade_ativa_id)
    receitas_recorrentes = ReceitaRecorrente.objects.filter(unidade_negocio_id=unidade_ativa_id)
    
    context = {
        'despesa_form': despesa_form,
        'receita_form': receita_form,
        'despesas_recorrentes': despesas_recorrentes,
        'receitas_recorrentes': receitas_recorrentes,
    }
    return render(request, 'finances/recorrencia_list.html', context)


@admin_required
def delete_despesa_recorrente_view(request, pk):
    if request.method == 'POST':
        recorrente = get_object_or_404(DespesaRecorrente, pk=pk)
        recorrente.delete()
        messages.success(request, 'Despesa recorrente deletada com sucesso!')
    return redirect('finances:recorrencia_list')


@admin_required
def edit_despesa_recorrente_view(request, pk):
    recorrente = get_object_or_404(DespesaRecorrente, pk=pk)
    if request.method == 'POST':
        form = DespesaRecorrenteForm(request.POST, instance=recorrente)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
    data = model_to_dict(recorrente)
    return JsonResponse(data)


@admin_required
def delete_receita_recorrente_view(request, pk):
    if request.method == 'POST':
        recorrente = get_object_or_404(ReceitaRecorrente, pk=pk)
        recorrente.delete()
        messages.success(request, 'Receita recorrente deletada com sucesso!')
    return redirect('finances:recorrencia_list')


@admin_required
def edit_receita_recorrente_view(request, pk):
    recorrente = get_object_or_404(ReceitaRecorrente, pk=pk)
    if request.method == 'POST':
        form = ReceitaRecorrenteForm(request.POST, instance=recorrente)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
    data = model_to_dict(recorrente)
    return JsonResponse(data)


@admin_required
def dre_view(request):
    unidade_ativa_id = request.session.get('unidade_ativa_id')
    if not unidade_ativa_id:
        messages.warning(request, "Selecione uma Unidade de Negócio.")
        return redirect('scheduler:dashboard')

    today = now().date()
    start_date = date.fromisoformat(request.GET.get('start_date')) if request.GET.get('start_date') else today.replace(day=1)
    end_date = date.fromisoformat(request.GET.get('end_date')) if request.GET.get('end_date') else (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    receitas_periodo = Receita.objects.filter(
        unidade_negocio_id=unidade_ativa_id,
        data_competencia__range=[start_date, end_date]
    )
    despesas_periodo = Despesa.objects.filter(
        unidade_negocio_id=unidade_ativa_id,
        data_competencia__range=[start_date, end_date]
    )

    total_receitas = receitas_periodo.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    total_custos = despesas_periodo.filter(categoria__tipo_dre='custo').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    total_despesas = despesas_periodo.filter(categoria__tipo_dre='despesa').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    lucro_bruto = total_receitas - total_custos
    resultado = lucro_bruto - total_despesas

    if total_receitas > 0:
        perc_custos = (total_custos / total_receitas * 100).quantize(Decimal('0.01'))
        perc_lucro_bruto = (lucro_bruto / total_receitas * 100).quantize(Decimal('0.01'))
        perc_despesas = (total_despesas / total_receitas * 100).quantize(Decimal('0.01'))
        perc_resultado = (resultado / total_receitas * 100).quantize(Decimal('0.01'))
    else:
        perc_custos = perc_lucro_bruto = perc_despesas = perc_resultado = Decimal('0.00')

    context = {
        'total_receitas': total_receitas,
        'custos_por_categoria': despesas_periodo.filter(categoria__tipo_dre='custo')
                                   .values('categoria__name').annotate(total_cat=Sum('valor')),
        'total_custos': total_custos,
        'lucro_bruto': lucro_bruto,
        'despesas_por_categoria': despesas_periodo.filter(categoria__tipo_dre='despesa')
                                       .values('categoria__name').annotate(total_cat=Sum('valor')),
        'total_despesas': total_despesas,
        'resultado': resultado,
        'perc_custos': perc_custos,
        'perc_lucro_bruto': perc_lucro_bruto,
        'perc_despesas': perc_despesas,
        'perc_resultado': perc_resultado,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'finances/dre_report.html', context)
