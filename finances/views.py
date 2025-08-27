from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Transaction
from .forms import TransactionForm, CategoryForm
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.forms.models import model_to_dict
from django.db.models import Sum
from django.core.paginator import Paginator
from datetime import date, timedelta
from django.utils.timezone import now
import calendar


def add_months(d: date, months: int) -> date:
    """Avança 'months' meses mantendo o dia possível mais próximo."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@login_required
def transaction_list_view(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    today = now().date()
    if not start_date_str:
        start_date = today.replace(day=1)
    else:
        start_date = date.fromisoformat(start_date_str)

    if not end_date_str:
        next_month = today.replace(day=28) + timedelta(days=4)
        end_date = next_month - timedelta(days=next_month.day)
    else:
        end_date = date.fromisoformat(end_date_str)

    transactions_in_period = Transaction.objects.filter(transaction_date__range=[start_date, end_date])

    paginator = Paginator(transactions_in_period, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

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
        # meses aproximados no período filtrado
        num_months_in_period = Decimal(str(num_days_in_period / 30.44))

        if num_months_in_period > 0:
            avg_monthly_income = total_income / num_months_in_period
            avg_monthly_expenses = total_expenses / num_months_in_period
        else:
            avg_monthly_income = avg_monthly_expenses = Decimal('0.00')

        # saldo de partida = saldo do período filtrado (o que já aparece no card "Saldo")
        monthly_net = avg_monthly_income - avg_monthly_expenses
        cumulative_balance = balance

        # projetar os PRÓXIMOS 6 MESES no calendário, a partir do fim do período filtrado
        for i in range(1, 7):
            future_month_date = add_months(end_date, i)
            cumulative_balance += monthly_net  # acumula mês a mês

            projection_data.append({
                'month': future_month_date.strftime("%b/%Y"),
                'income': avg_monthly_income,
                'expenses': avg_monthly_expenses,
                'balance': cumulative_balance,  # <-- AGORA É ACUMULADO
            })

    form = TransactionForm()
    if request.method == "POST":
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            transaction.save()
            messages.success(request, "Lançamento adicionado com sucesso!")
            return redirect(request.get_full_path())

    context = {
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
