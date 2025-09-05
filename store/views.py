from django.shortcuts import render, redirect, get_object_or_404
from django.forms.models import model_to_dict
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib import messages
from django.http import JsonResponse
from .models import Produto, CategoriaProduto
from .forms import ProdutoForm, CategoriaProdutoForm
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Q


def admin_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.tipo == 'admin':
            messages.error(request, "Você não tem permissão para acessar esta página.")
            return redirect('scheduler:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@admin_required
def produto_list_view(request):
    unidade_ativa_id = request.session.get('unidade_ativa_id')
    if not unidade_ativa_id:
        messages.warning(request, "Por favor, selecione uma Unidade de Negócio.")
        return redirect('scheduler:dashboard')

    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.unidade_negocio_id = unidade_ativa_id
            produto.save()
            messages.success(request, 'Produto cadastrado com sucesso!')
            return redirect('store:produto_list')
    else:
        form = ProdutoForm()

    produtos_list = Produto.objects.filter(unidade_negocio_id=unidade_ativa_id).order_by('nome')

    produtos_list = produtos_list.annotate(
        quantidade_vendida=Sum('receitas__quantidade', filter=Q(receitas__unidade_negocio_id=unidade_ativa_id))
    )

    search_query = request.GET.get('q', '')
    category_filter = request.GET.get('categoria', '')
    stock_filter = request.GET.get('estoque', '')

    if search_query:
        produtos_list = produtos_list.filter(
            Q(nome__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(categoria__nome__icontains=search_query)
        )

    if category_filter:
        produtos_list = produtos_list.filter(categoria__id=category_filter)

    if stock_filter == 'baixo':
        produtos_list = produtos_list.filter(quantidade_em_estoque__lte=5)

    paginator = Paginator(produtos_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categorias = CategoriaProduto.objects.filter(unidade_negocio_id=unidade_ativa_id)
    
    context = {
        'produtos': page_obj,
        'search_query': search_query,
        'categorias': categorias,
        'category_filter': category_filter,
        'stock_filter': stock_filter,
        'form': form,
    }
    return render(request, 'store/produto_list.html', context)


class ProdutoCreateView(CreateView):
    model = Produto
    form_class = ProdutoForm
    template_name = "store/produto_form.html"
    success_url = reverse_lazy("store:produto_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Adicionar Novo Produto"
        return context

    def form_valid(self, form):
        form.instance.unidade_negocio_id = self.request.session.get("unidade_ativa_id")
        messages.success(self.request, "Produto cadastrado com sucesso!")
        return super().form_valid(form)


@admin_required
def produto_edit_view(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors.as_json()})
    
    data = model_to_dict(produto)
    return JsonResponse(data)


@login_required
def produto_delete_view(request, pk):
    if request.method == 'POST' and request.user.tipo == 'admin':
        produto = get_object_or_404(Produto, pk=pk)
        messages.success(request, f'Produto "{produto.nome}" excluído com sucesso.')
        produto.delete()
        return redirect('store:produto_list')
    else:
        messages.error(request, "Ação não permitida.")
        return redirect('store:produto_list')


def add_categoria_produto_ajax(request):
    if request.method == "POST":
        form = CategoriaProdutoForm(request.POST)
        if form.is_valid():
            categoria = form.save(commit=False)
            categoria.unidade_negocio_id = request.session.get("unidade_ativa_id")
            categoria.save()
            return JsonResponse(
                {"status": "success", "id": categoria.id, "name": categoria.nome}
            )
        else:
            return JsonResponse({"status": "error", "errors": form.errors})
    return JsonResponse({"status": "error"})


def get_produto_details_ajax(request, pk):
    try:
        produto = Produto.objects.get(pk=pk)
        data = {
            'preco': produto.preco_de_venda_calculado,
            'estoque': produto.quantidade_em_estoque
        }
        return JsonResponse(data)
    except Produto.DoesNotExist:
        return JsonResponse({'error': 'Produto não encontrado'}, status=404)
