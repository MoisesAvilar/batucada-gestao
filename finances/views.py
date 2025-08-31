from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Transaction, Despesa, Receita, DespesaRecorrente, ReceitaRecorrente, Category
from .forms import TransactionForm, CategoryForm, DespesaForm, ReceitaForm, DespesaRecorrenteForm, ReceitaRecorrenteForm
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.forms.models import model_to_dict
from django.db.models import Sum
from django.core.paginator import Paginator
from datetime import date, timedelta
from django.utils.timezone import now


def add_months(start_date, months):
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(start_date.day, [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month])
    return date(year, month, day)


@login_required
def transaction_list_view(request):
    MESES_PT = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
        5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
    }
    unidade_ativa_id = request.session.get('unidade_ativa_id')
    if not unidade_ativa_id:
        messages.warning(request, "Por favor, selecione uma Unidade de Negócio para continuar.")
        return redirect('scheduler:dashboard')

    # --- LÓGICA DE FILTRO DE DATA CORRIGIDA ---
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    today = now().date()

    # Garante que start_date SEMPRE terá um valor
    if start_date_str:
        start_date = date.fromisoformat(start_date_str)
    else:
        start_date = today.replace(day=1)

    # Garante que end_date SEMPRE terá um valor
    if end_date_str:
        end_date = date.fromisoformat(end_date_str)
    else:
        next_month = today.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day)
    # --- FIM DA CORREÇÃO ---

    total_a_pagar = Despesa.objects.filter(
        unidade_negocio_id=unidade_ativa_id,
        status='a_pagar',
        data_competencia__range=[start_date, end_date]
    ).aggregate(total=Sum('valor'))['total'] or 0

    # Busca o total de receitas "A Receber" com competência no período filtrado
    total_a_receber = Receita.objects.filter(
        unidade_negocio_id=unidade_ativa_id,
        status='a_receber',
        data_competencia__range=[start_date, end_date]
    ).aggregate(total=Sum('valor'))['total'] or 0

    transactions_in_period = Transaction.objects.filter(
        unidade_negocio_id=unidade_ativa_id,
        transaction_date__range=[start_date, end_date]
    )

    total_income = transactions_in_period.filter(category__type='income').aggregate(total=Sum('amount'))['total'] or 0
    total_expenses = transactions_in_period.filter(category__type='expense').aggregate(total=Sum('amount'))['total'] or 0
    balance = total_income - total_expenses

    expenses_by_category = (
        transactions_in_period.filter(category__type='expense')
        .values('category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    chart_labels = [item['category__name'] for item in expenses_by_category]
    chart_data = [float(item['total']) for item in expenses_by_category]

    projection_data = []
    num_days_in_period = (end_date - start_date).days + 1

    if num_days_in_period >= 15:
        # Meses em português (nome completo)
        MESES_PT = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }

    months_spanned = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1

    if months_spanned > 0:
        avg_monthly_income = Decimal(total_income) / Decimal(months_spanned)
        avg_monthly_expenses = Decimal(total_expenses) / Decimal(months_spanned)
    else:
        avg_monthly_income = avg_monthly_expenses = Decimal('0.00')

    cumulative_balance = balance
    monthly_net = avg_monthly_income - avg_monthly_expenses

    # Projeção próximos 6 meses
    for i in range(1, 7):
        future_date = add_months(end_date.replace(day=1), i)
        cumulative_balance += monthly_net
        projection_data.append({
            'month': f"{MESES_PT[future_date.month]}/{future_date.year}",
            'income': avg_monthly_income,
            'expenses': avg_monthly_expenses,
            'balance': cumulative_balance,
        })

    paginator = Paginator(transactions_in_period, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    form = TransactionForm(initial={'unidade_negocio': unidade_ativa_id})
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            transaction.unidade_negocio_id = unidade_ativa_id
            transaction.save()
            messages.success(request, "Lançamento adicionado com sucesso!")
            return redirect(request.get_full_path())
    
    context = {
        'page_obj': page_obj, 'form': form, 'total_income': total_income,
        'total_expenses': total_expenses, 'balance': balance,
        'start_date': start_date, 'end_date': end_date,
        'chart_labels': chart_labels, 'chart_data': chart_data,
        'projection_data': projection_data,
        'total_a_pagar': total_a_pagar, 'total_a_receber': total_a_receber,
    }
    return render(request, 'finances/transaction_list.html', context)


@login_required
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


@login_required
def delete_transaction_view(request, pk):
    if request.method == "POST":
        transaction = get_object_or_404(Transaction, pk=pk)
        transaction.delete()
        messages.success(request, "Lançamento deletado com sucesso!")
    return redirect("finances:transaction_list")


@login_required
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


@login_required
def despesa_list_view(request):
    unidade_ativa_id = request.session.get('unidade_ativa_id')
    if not unidade_ativa_id:
        messages.warning(request, "Selecione uma Unidade de Negócio.")
        return redirect('scheduler:dashboard')

    if request.method == 'POST':
        form = DespesaForm(request.POST)
        if form.is_valid():
            despesa = form.save(commit=False)
            despesa.unidade_negocio_id = unidade_ativa_id
            
            # Se o usuário já informou a data de pagamento, a despesa já entra como 'paga'
            if despesa.data_pagamento:
                despesa.status = 'pago'
                # E já criamos a transação no fluxo de caixa
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

    despesas = Despesa.objects.filter(unidade_negocio_id=unidade_ativa_id).order_by('-data_competencia')
    context = {'form': form, 'despesas': despesas}
    return render(request, 'finances/despesa_list.html', context)


# NOVA VIEW PARA "BAIXAR" UMA DESPESA
@login_required
def baixar_despesa_view(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk)
    if request.method == 'POST':
        data_pagamento_str = request.POST.get('data_pagamento')
        juros_multa_str = request.POST.get('juros_multa') # Pega o valor dos juros

        if data_pagamento_str:
            data_pagamento = date.fromisoformat(data_pagamento_str)
            
            # --- LÓGICA PRINCIPAL ATUALIZADA ---
            # 1. Cria a transação para o valor principal
            transacao_principal = Transaction.objects.create(
                unidade_negocio_id=despesa.unidade_negocio.id,
                description=f"Pagamento: {despesa.descricao}",
                amount=despesa.valor,
                category=despesa.categoria,
                transaction_date=data_pagamento,
                professor=despesa.professor,
                created_by=request.user
            )
            
            # 2. Atualiza a despesa, ligando-a à transação principal
            despesa.status = 'pago'
            despesa.data_pagamento = data_pagamento
            despesa.transacao = transacao_principal
            despesa.save()

            # 3. Se houver juros, cria uma transação separada para eles
            if juros_multa_str and Decimal(juros_multa_str) > 0:
                try:
                    # Busca a categoria "Juros e Multas Pagas" que criamos
                    categoria_juros = Category.objects.get(name__iexact="Juros e Multas Pagas", type="expense")
                    Transaction.objects.create(
                        unidade_negocio_id=despesa.unidade_negocio.id,
                        description=f"Juros/Multa Ref: {despesa.descricao}",
                        amount=Decimal(juros_multa_str),
                        category=categoria_juros,
                        transaction_date=data_pagamento,
                        created_by=request.user
                    )
                    messages.success(request, f'Despesa e Juros de R$ {juros_multa_str} baixados com sucesso!')
                except Category.DoesNotExist:
                    messages.error(request, 'Categoria "Juros e Multas Pagas" não encontrada. Juros não registrados.')
            else:
                messages.success(request, 'Despesa baixada com sucesso!')
            # --- FIM DA LÓGICA ATUALIZADA ---
            
    return redirect('finances:despesa_list')


@login_required
def delete_despesa_view(request, pk):
    # Apenas requisições POST podem deletar por segurança
    if request.method == 'POST':
        despesa = get_object_or_404(Despesa, pk=pk)
        # Se a despesa já tiver uma transação de caixa associada, ela também deve ser deletada
        if despesa.transacao:
            despesa.transacao.delete()
        despesa.delete()
        messages.success(request, 'Despesa deletada com sucesso!')
    return redirect('finances:despesa_list')

@login_required
def edit_despesa_view(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk)
    if request.method == 'POST':
        form = DespesaForm(request.POST, instance=despesa)
        if form.is_valid():
            form.save() # O formulário já lida com a atualização
            return JsonResponse({'status': 'success', 'despesa': model_to_dict(despesa)})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
    
    # Para GET, retorna os dados para preencher o modal
    data = model_to_dict(despesa)
    return JsonResponse(data)


@login_required
def receita_list_view(request):
    unidade_ativa_id = request.session.get('unidade_ativa_id')
    # ... (verificação da unidade ativa) ...

    if request.method == 'POST':
        form = ReceitaForm(request.POST)
        if form.is_valid():
            receita = form.save(commit=False)
            receita.unidade_negocio_id = unidade_ativa_id
            
            # Se a data de recebimento for informada, já baixa automaticamente
            if receita.data_recebimento:
                receita.status = 'recebido'
                transacao = Transaction.objects.create(
                    unidade_negocio_id=unidade_ativa_id,
                    description=f"Recebimento: {receita.descricao}",
                    amount=receita.valor,
                    category=receita.categoria,
                    transaction_date=receita.data_recebimento,
                    student=receita.aluno, # Associa o aluno à transação de caixa
                    created_by=request.user
                )
                receita.transacao = transacao
            
            receita.save()
            messages.success(request, 'Receita registrada com sucesso!')
            return redirect('finances:receita_list')
    else:
        form = ReceitaForm()

    receitas = Receita.objects.filter(unidade_negocio_id=unidade_ativa_id).order_by('-data_competencia')
    context = {'form': form, 'receitas': receitas}
    return render(request, 'finances/receita_list.html', context)

# NOVA VIEW PARA "BAIXAR" UMA RECEITA
@login_required
def baixar_receita_view(request, pk):
    receita = get_object_or_404(Receita, pk=pk)
    if request.method == 'POST':
        data_recebimento_str = request.POST.get('data_recebimento')
        if data_recebimento_str:
            data_recebimento = date.fromisoformat(data_recebimento_str)
            
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
            
    return redirect('finances:receita_list')


@login_required
def delete_receita_view(request, pk):
    if request.method == 'POST':
        receita = get_object_or_404(Receita, pk=pk)
        # Se houver uma transação de caixa associada, também a removemos
        if receita.transacao:
            receita.transacao.delete()
        receita.delete()
        messages.success(request, 'Receita deletada com sucesso!')
    return redirect('finances:receita_list')


@login_required
def edit_receita_view(request, pk):
    receita = get_object_or_404(Receita, pk=pk)
    if request.method == 'POST':
        form = ReceitaForm(request.POST, instance=receita)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success', 'receita': model_to_dict(receita)})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
    
    # Para GET, retorna os dados para preencher o modal
    data = model_to_dict(receita)
    return JsonResponse(data)


@login_required
def recorrencia_list_view(request):
    unidade_ativa_id = request.session.get('unidade_ativa_id')
    # ... (verificação da unidade ativa) ...

    # Lógica para adicionar uma nova Despesa Recorrente
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

    # Lógica para adicionar uma nova Receita Recorrente
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


@login_required
def delete_despesa_recorrente_view(request, pk):
    if request.method == 'POST':
        recorrente = get_object_or_404(DespesaRecorrente, pk=pk)
        recorrente.delete()
        messages.success(request, 'Despesa recorrente deletada com sucesso!')
    return redirect('finances:recorrencia_list')


@login_required
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


@login_required
def delete_receita_recorrente_view(request, pk):
    if request.method == 'POST':
        recorrente = get_object_or_404(ReceitaRecorrente, pk=pk)
        recorrente.delete()
        messages.success(request, 'Receita recorrente deletada com sucesso!')
    return redirect('finances:recorrencia_list')


@login_required
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


@login_required
def dre_view(request):
    unidade_ativa_id = request.session.get('unidade_ativa_id')
    if not unidade_ativa_id:
        messages.warning(request, "Por favor, selecione uma Unidade de Negócio para continuar.")
        return redirect('scheduler:dashboard')

    # Lógica de filtro de data (igual ao dashboard)
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    today = now().date()

    if start_date_str:
        start_date = date.fromisoformat(start_date_str)
    else:
        start_date = today.replace(day=1)

    if end_date_str:
        end_date = date.fromisoformat(end_date_str)
    else:
        next_month = today.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day)

    # --- LÓGICA PRINCIPAL DO DRE ---
    # Buscamos TODAS as receitas e despesas pela DATA DE COMPETÊNCIA
    receitas_periodo = Receita.objects.filter(
        unidade_negocio_id=unidade_ativa_id,
        data_competencia__range=[start_date, end_date]
    )
    despesas_periodo = Despesa.objects.filter(
        unidade_negocio_id=unidade_ativa_id,
        data_competencia__range=[start_date, end_date]
    )

    # Calculamos os totais
    total_receitas = receitas_periodo.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    total_despesas = despesas_periodo.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    total_receitas = receitas_periodo.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    
    # Separamos os gastos em Custos e Despesas
    total_custos = despesas_periodo.filter(categoria__tipo_dre='custo').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
    total_despesas = despesas_periodo.filter(categoria__tipo_dre='despesa').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

    # Novos cálculos
    lucro_bruto = total_receitas - total_custos
    resultado = lucro_bruto - total_despesas
    
    # DRE Simplificado: Resultado do Exercício
    resultado = total_receitas - total_despesas

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

    # --- INÍCIO DA CORREÇÃO: CÁLCULO DAS PORCENTAGENS ---
    if total_receitas > 0:
        perc_custos = (total_custos / total_receitas) * 100
        perc_lucro_bruto = (lucro_bruto / total_receitas) * 100
        perc_despesas = (total_despesas / total_receitas) * 100
        perc_resultado = (resultado / total_receitas) * 100
    else:
        # Evita divisão por zero se não houver receita
        perc_custos = perc_lucro_bruto = perc_despesas = perc_resultado = Decimal('0.00')
    # --- FIM DA CORREÇÃO ---

    context = {
        'total_receitas': total_receitas,
        'custos_por_categoria': despesas_periodo.filter(categoria__tipo_dre='custo').values('categoria__name').annotate(total_cat=Sum('valor')),
        'total_custos': total_custos,
        'lucro_bruto': lucro_bruto,
        'despesas_por_categoria': despesas_periodo.filter(categoria__tipo_dre='despesa').values('categoria__name').annotate(total_cat=Sum('valor')),
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
