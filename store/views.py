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
from django.db.models import Q


def admin_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.tipo == 'admin':
            messages.error(request, "Você não tem permissão para acessar esta página.")
            return redirect('scheduler:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# View para listar os produtos

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

    # --- INÍCIO DA CORREÇÃO ---
    # 1. Usamos apenas uma variável para a lista de produtos.
    produtos_list = Produto.objects.filter(unidade_negocio_id=unidade_ativa_id).order_by('nome')
    
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
        # Consideramos 'baixo estoque' como 5 unidades ou menos.
        produtos_list = produtos_list.filter(quantidade_em_estoque__lte=5)

    # 2. A paginação é feita sobre a lista já filtrada.
    paginator = Paginator(produtos_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categorias = CategoriaProduto.objects.filter(unidade_negocio_id=unidade_ativa_id)
    
    context = {
        'produtos': page_obj, # 3. Enviamos o objeto da página na variável 'produtos'.
        'search_query': search_query,
        'categorias': categorias, # <-- Novo contexto
        'category_filter': category_filter, # <-- Novo contexto
        'stock_filter': stock_filter,
        'form': form,
    }
    # --- FIM DA CORREÇÃO ---
    return render(request, 'store/produto_list.html', context)


# View para criar um novo produto

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


# View para editar um produto

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
    
    # Para GET, retorna os dados do produto para preencher o modal
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


# View AJAX para criar Categoria de Produto
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
