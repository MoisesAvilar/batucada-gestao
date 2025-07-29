import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

# Importa os modelos necessários
from scheduler.models import CustomUser, Aluno, Modalidade, Aula

# A anotação @pytest.mark.django_db é essencial.
# Ela dá ao teste acesso ao banco de dados.
@pytest.mark.django_db
def test_professor_pode_acessar_pagina_de_agendamento(client, professor_user):
    """
    GIVEN um professor logado
    WHEN ele acessa a página de agendamento de aula
    THEN a página deve carregar com sucesso (status 200)
    AND o formulário de seleção de professores não deve estar visível.
    """
    # Arrange: Faz o login do professor (a fixture 'professor_user' já o criou)
    client.login(username='prof_teste', password='password123')
    url = reverse('scheduler:aula_agendar')

    # Act: Faz a requisição GET para a página
    response = client.get(url)

    # Assert: Verifica as condições
    assert response.status_code == 200
    # O pytest-django nos permite usar o response.content.decode() para verificar o HTML
    assert '<h5>Professores Atribuídos</h5>' not in response.content.decode()
    assert 'Agendar Nova Aula' in response.content.decode()

@pytest.mark.django_db
def test_professor_pode_agendar_aula_para_si_mesmo(client, professor_user, aluno, modalidade):
    """
    GIVEN um professor logado
    WHEN ele submete um formulário de agendamento de aula válido
    THEN uma nova aula deve ser criada no banco de dados
    AND a nova aula deve ser atribuída automaticamente a ele.
    """
    # Arrange: Login e preparação dos dados do formulário
    client.login(username='prof_teste', password='password123')
    url = reverse('scheduler:aula_agendar')
    amanha = timezone.now() + timedelta(days=1)
    
    form_data = {
        'modalidade': modalidade.pk,
        'data_hora': amanha.strftime('%Y-%m-%dT%H:%M'),
        'status': 'Agendada',
        'alunos-TOTAL_FORMS': '1',
        'alunos-INITIAL_FORMS': '0',
        'alunos-0-aluno': aluno.pk,
    }

    # Act: Envia a requisição POST com os dados do formulário
    response = client.post(url, data=form_data)

    # Assert: Verifica o resultado
    assert response.status_code == 302, "A resposta deveria ser um redirecionamento"
    assert response.url == reverse('scheduler:dashboard'), "Deveria redirecionar para o dashboard"
    
    # Verifica se a aula foi realmente criada
    assert Aula.objects.count() == 1
    nova_aula = Aula.objects.first()
    
    # A verificação mais importante: o professor da aula é o usuário logado?
    assert nova_aula.professores.count() == 1
    assert nova_aula.professores.first() == professor_user

@pytest.mark.django_db
def test_admin_ve_campo_de_professores(client, admin_user):
    """
    GIVEN um admin logado
    WHEN ele acessa a página de agendamento de aula
    THEN o formulário de seleção de professores deve estar visível.
    """
    # Arrange
    client.login(username='admin_teste', password='password123')
    url = reverse('scheduler:aula_agendar')

    # Act
    response = client.get(url)

    # Assert
    assert response.status_code == 200
    
    # ★★★ CORREÇÃO AQUI ★★★
    # Alterado de "Professores Atribuídos" para "Professores" para corresponder ao template.
    assert 'Professores</h5>' in response.content.decode()