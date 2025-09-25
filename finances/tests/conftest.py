import pytest
from finances.models import Category
from scheduler.models import Aluno
from core.models import UnidadeNegocio # ★★★ 1. IMPORTE O MODELO ★★★

# ★★★ 2. CRIE A FIXTURE PARA A UNIDADE DE NEGÓCIO ★★★
@pytest.fixture
def unidade_negocio(db):
    """Fixture para uma Unidade de Negócio de teste."""
    return UnidadeNegocio.objects.create(nome='Unidade Teste')

# ★★★ 3. ATUALIZE AS FIXTURES DE CATEGORIA PARA USAR A UNIDADE ★★★
@pytest.fixture
def categoria_despesa(db, unidade_negocio):
    """Fixture para uma categoria de Despesa."""
    return Category.objects.create(
        name='Aluguel',
        type='expense',
        unidade_negocio=unidade_negocio # Associa a unidade
    )

@pytest.fixture
def categoria_receita(db, unidade_negocio):
    """Fixture para uma categoria de Receita."""
    return Category.objects.create(
        name='Mensalidade',
        type='income',
        unidade_negocio=unidade_negocio # Associa a unidade
    )

@pytest.fixture
def aluno_ativo(db):
    """Fixture para um aluno com status ativo."""
    return Aluno.objects.create(
        nome_completo='Aluno Ativo Teste',
        status='ativo',
        dia_vencimento=10,
        valor_mensalidade=300.00
    )

@pytest.fixture
def aluno_inativo(db):
    """Fixture para um aluno com status inativo."""
    return Aluno.objects.create(
        nome_completo='Aluno Inativo Teste',
        status='inativo',
        dia_vencimento=10,
        valor_mensalidade=300.00
    )