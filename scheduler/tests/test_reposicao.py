# scheduler/tests/test_reposicao.py

import pytest
from django.urls import reverse
from scheduler.models import Aula, PresencaAluno
from django.utils import timezone

@pytest.mark.django_db
def test_fluxo_completo_de_reposicao(client, admin_user, aluno, modalidade):
    """
    GIVEN uma falta justificada registrada
    WHEN um admin agenda uma aula de reposição através do link correto
    THEN a nova aula é criada E a falta original é vinculada a ela.
    """
    # 1. Arrange: Criar a falta justificada original
    # ---------------------------------------------
    client.login(username='admin_teste', password='password123')
    aula_original = Aula.objects.create(
        modalidade=modalidade, 
        data_hora=timezone.make_aware(timezone.datetime(2025, 10, 1, 10, 0)),
        status='Aluno Ausente' # Simulando que já foi validada
    )
    aula_original.alunos.set([aluno])
    falta_original = PresencaAluno.objects.create(
        aula=aula_original, 
        aluno=aluno, 
        status='ausente', 
        tipo_falta='justificada'
    )
    
    # Verifica o estado inicial
    assert falta_original.aula_reposicao is None
    assert Aula.objects.count() == 1

    # 2. Act: Simular o agendamento da reposição
    # -----------------------------------------
    # O admin clica no link da página "Controle de Reposições"
    url_agendamento = f"{reverse('scheduler:aula_agendar')}?reposicao_de={falta_original.id}"
    
    # Prepara os dados do formulário para a nova aula
    form_data = {
        'modalidade': modalidade.pk,
        'data_hora': '2025-10-08T11:00:00', # Uma semana depois
        'status': 'Agendada',
        'reposicao_de_id': falta_original.id, # O campo hidden do formulário
        'alunos-TOTAL_FORMS': '1',
        'alunos-INITIAL_FORMS': '0',
        'alunos-0-aluno': aluno.pk,
        'professores-TOTAL_FORMS': '1',
        'professores-INITIAL_FORMS': '0',
        'professores-0-professor': admin_user.pk,
    }

    # Envia o POST para criar a aula de reposição
    client.post(url_agendamento, data=form_data)

    # 3. Assert: Verificar se tudo foi conectado corretamente
    # -----------------------------------------------------
    # Devemos ter duas aulas no total agora
    assert Aula.objects.count() == 2
    aula_de_reposicao = Aula.objects.latest('id') # Pega a última aula criada

    # Recarrega a falta original do banco para ver a atualização
    falta_original.refresh_from_db()
    
    # A verificação mais importante: a falta original agora aponta para a nova aula?
    assert falta_original.aula_reposicao == aula_de_reposicao