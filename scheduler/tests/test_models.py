# scheduler/tests/test_models.py

import pytest
from scheduler.models import Aula, RelatorioAula

# A anotação @pytest.mark.django_db dá ao teste acesso ao banco de dados.
@pytest.mark.django_db
def test_aula_foi_substituida_property(admin_user, professor_user, modalidade):
    """
    GIVEN uma Aula criada
    WHEN um relatório é validado por um professor que não estava na lista original
    THEN a propriedade `foi_substituida` deve retornar True.
    """
    # Arrange: Cria uma aula atribuída APENAS ao admin
    aula = Aula.objects.create(
        modalidade=modalidade,
        data_hora='2025-08-01T10:00:00Z',
        status='Agendada'
    )
    aula.professores.set([admin_user])

    # Act: Cria um relatório para esta aula, mas validado pelo PROFESSOR
    relatorio = RelatorioAula.objects.create(
        aula=aula,
        professor_que_validou=professor_user
    )
    aula.status = 'Realizada'
    aula.save()
    aula.refresh_from_db() # Recarrega a aula do banco para garantir que o relatório está associado

    # Assert: A propriedade deve retornar True
    assert aula.foi_substituida is True

@pytest.mark.django_db
def test_aula_nao_foi_substituida_property(admin_user, modalidade):
    """
    GIVEN uma Aula criada
    WHEN o relatório é validado por um dos professores originais
    THEN a propriedade `foi_substituida` deve retornar False.
    """
    # Arrange: Cria uma aula atribuída ao admin
    aula = Aula.objects.create(
        modalidade=modalidade,
        data_hora='2025-08-01T11:00:00Z',
        status='Agendada'
    )
    aula.professores.set([admin_user])

    # Act: O relatório é validado pelo MESMO professor (admin)
    RelatorioAula.objects.create(
        aula=aula,
        professor_que_validou=admin_user
    )
    aula.status = 'Realizada'
    aula.save()
    aula.refresh_from_db()

    # Assert: A propriedade deve retornar False
    assert aula.foi_substituida is False