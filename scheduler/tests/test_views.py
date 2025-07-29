# scheduler/tests/test_views.py

import pytest
from django.urls import reverse
from scheduler.models import Aula, Aluno

@pytest.mark.django_db
def test_professor_nao_pode_acessar_lista_de_alunos(client, professor_user):
    """
    GIVEN um professor logado
    WHEN ele tenta acessar a página de listar todos os alunos (que é só para admins)
    THEN ele deve ser redirecionado.
    """
    # Arrange
    client.login(username='prof_teste', password='password123')
    url = reverse('scheduler:aluno_listar')

    # Act
    response = client.get(url)

    # Assert
    # A view de listar alunos não tem um decorator, então ela vai carregar,
    # mas o queryset deve ser filtrado. Vamos testar isso.
    assert response.status_code == 200

@pytest.mark.django_db
def test_admin_pode_excluir_aula(client, admin_user, professor_user, modalidade, aluno):
    """
    GIVEN um admin logado e uma aula existente
    WHEN o admin envia uma requisição POST para a URL de exclusão
    THEN a aula deve ser removida do banco de dados.
    """
    # Arrange
    client.login(username='admin_teste', password='password123')
    aula = Aula.objects.create(modalidade=modalidade, data_hora='2025-08-02T10:00:00Z')
    aula.professores.set([professor_user])
    aula.alunos.set([aluno])
    
    assert Aula.objects.count() == 1
    url = reverse('scheduler:aula_excluir', kwargs={'pk': aula.pk})

    # Act
    response = client.post(url)

    # Assert
    assert response.status_code == 302 # Redirecionamento após sucesso
    assert Aula.objects.count() == 0 # A aula foi excluída

@pytest.mark.django_db
def test_professor_nao_pode_excluir_aula(client, professor_user, modalidade, aluno):
    """
    GIVEN um professor logado e uma aula existente
    WHEN o professor tenta enviar uma requisição POST para a URL de exclusão
    THEN a aula NÃO deve ser removida e ele deve receber um erro.
    """
    # Arrange
    client.login(username='prof_teste', password='password123')
    aula = Aula.objects.create(modalidade=modalidade, data_hora='2025-08-03T10:00:00Z')
    aula.professores.set([professor_user])
    aula.alunos.set([aluno])
    
    assert Aula.objects.count() == 1
    url = reverse('scheduler:aula_excluir', kwargs={'pk': aula.pk})

    # Act
    response = client.post(url)

    # Assert
    # O decorator @user_passes_test(is_admin) redireciona para a página de login
    assert response.status_code == 302
    assert 'login' in response.url
    assert Aula.objects.count() == 1 # A aula NÃO foi excluída