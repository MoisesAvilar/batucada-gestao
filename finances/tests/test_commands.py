# finances/tests/test_commands.py

import pytest
from django.core.management import call_command
from django.utils import timezone
from finances.models import Despesa, Receita, DespesaRecorrente, ReceitaRecorrente

@pytest.mark.django_db
def test_gera_despesa_recorrente_com_sucesso(categoria_despesa, unidade_negocio):
    """
    GIVEN uma despesa recorrente ativa
    WHEN o comando gerar_lancamentos_recorrentes é executado
    THEN uma nova Despesa deve ser criada para o mês atual.
    """
    # Arrange
    hoje = timezone.now().date()
    DespesaRecorrente.objects.create(
        unidade_negocio=unidade_negocio,
        descricao='Teste de Aluguel',
        valor=1500.00,
        categoria=categoria_despesa,
        dia_do_mes=hoje.day,
        ativa=True
    )
    assert Despesa.objects.count() == 0

    # Act
    call_command('gerar_lancamentos_recorrentes')

    # Assert
    assert Despesa.objects.count() == 1
    nova_despesa = Despesa.objects.first()
    assert nova_despesa.descricao == 'Teste de Aluguel'
    assert nova_despesa.data_competencia.month == hoje.month
    assert nova_despesa.data_competencia.year == hoje.year

@pytest.mark.django_db
def test_nao_gera_despesa_duplicada(categoria_despesa, unidade_negocio):
    """
    GIVEN uma despesa recorrente que já foi lançada neste mês
    WHEN o comando é executado novamente
    THEN nenhuma nova Despesa deve ser criada.
    """
    # Arrange
    hoje = timezone.now().date()
    recorrente = DespesaRecorrente.objects.create(
        unidade_negocio=unidade_negocio,
        descricao='Teste de Aluguel',
        valor=1500.00,
        categoria=categoria_despesa,
        dia_do_mes=hoje.day,
        ativa=True
    )
    # Lança a despesa manualmente para simular que já existe
    Despesa.objects.create(
        unidade_negocio=unidade_negocio,
        descricao=recorrente.descricao,
        valor=recorrente.valor,
        categoria=recorrente.categoria,
        data_competencia=hoje.replace(day=recorrente.dia_do_mes)
    )
    assert Despesa.objects.count() == 1

    # Act
    call_command('gerar_lancamentos_recorrentes')

    # Assert
    assert Despesa.objects.count() == 1 # A contagem deve permanecer 1

@pytest.mark.django_db
def test_nao_gera_receita_para_aluno_inativo(categoria_receita, aluno_inativo, unidade_negocio):
    """
    GIVEN uma receita recorrente associada a um aluno inativo
    WHEN o comando é executado
    THEN nenhuma nova Receita deve ser criada para este aluno.
    """
    # Arrange
    hoje = timezone.now().date()
    # Força o dia de vencimento do aluno a ser hoje para o teste
    aluno_inativo.dia_vencimento = hoje.day
    aluno_inativo.save()

    ReceitaRecorrente.objects.create(
        unidade_negocio=unidade_negocio,
        descricao='Mensalidade Aluno Inativo',
        categoria=categoria_receita,
        aluno=aluno_inativo,
        ativa=True
    )
    assert Receita.objects.count() == 0

    # Act
    call_command('gerar_lancamentos_recorrentes')

    # Assert
    assert Receita.objects.count() == 0

@pytest.mark.django_db
def test_gera_receita_para_aluno_ativo(categoria_receita, aluno_ativo, unidade_negocio):
    """
    GIVEN uma receita recorrente associada a um aluno ativo
    WHEN o comando é executado
    THEN uma nova Receita de mensalidade deve ser criada.
    """
    # Arrange
    hoje = timezone.now().date()
    aluno_ativo.dia_vencimento = hoje.day
    aluno_ativo.save()

    ReceitaRecorrente.objects.create(
        unidade_negocio=unidade_negocio,
        descricao='Mensalidade Aluno Ativo',
        categoria=categoria_receita,
        aluno=aluno_ativo,
        ativa=True
    )
    assert Receita.objects.count() == 0

    # Act
    call_command('gerar_lancamentos_recorrentes')

    # Assert
    assert Receita.objects.count() == 1
    nova_receita = Receita.objects.first()
    assert nova_receita.aluno == aluno_ativo
    assert nova_receita.valor == aluno_ativo.valor_mensalidade