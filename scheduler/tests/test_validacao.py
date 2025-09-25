# scheduler/tests/test_validacao.py

import pytest
from django.urls import reverse
from scheduler.models import Aula, RelatorioAula, PresencaAluno
from django.utils import timezone

@pytest.mark.django_db
def test_professor_valida_aula_com_sucesso(client, professor_user, aluno, modalidade):
    # Este teste já estava passando e continua correto. Nenhuma alteração necessária.
    client.login(username='prof_teste', password='password123')
    aula = Aula.objects.create(
        modalidade=modalidade,
        data_hora=timezone.make_aware(timezone.datetime(2025, 8, 5, 10, 0)),
        status='Agendada'
    )
    aula.professores.set([professor_user])
    aula.alunos.set([aluno])
    presenca = PresencaAluno.objects.create(aula=aula, aluno=aluno, status='presente')
    url = reverse('scheduler:aula_validar', kwargs={'pk': aula.pk})
    
    report_data = {
        'conteudo_teorico': 'Estudamos a teoria das semicolcheias.',
        'observacoes_gerais': 'Ótimo desempenho do aluno.',
        'presencas_alunos-TOTAL_FORMS': '1',
        'presencas_alunos-INITIAL_FORMS': '1',
        'presencas_alunos-0-id': presenca.id,
        'presencas_alunos-0-status': 'presente',
        'presencas_alunos-0-tipo_falta': 'injustificada',
        'rudimentos-TOTAL_FORMS': '1',
        'rudimentos-INITIAL_FORMS': '0',
        'rudimentos-0-descricao': 'Toque Simples',
        'rudimentos-0-bpm': '120',
        'ritmo-TOTAL_FORMS': '0', 'ritmo-INITIAL_FORMS': '0',
        'viradas-TOTAL_FORMS': '0', 'viradas-INITIAL_FORMS': '0',
    }

    response = client.post(url, data=report_data)
    
    assert response.status_code == 302
    assert response.url == reverse('scheduler:aula_validar', kwargs={'pk': aula.pk})

    aula.refresh_from_db()
    assert aula.status == 'Realizada'
    relatorio = aula.relatorioaula
    assert relatorio.conteudo_teorico == 'Estudamos a teoria das semicolcheias.'
    assert relatorio.professor_que_validou == professor_user
    assert relatorio.itens_rudimentos.count() == 1
    presenca.refresh_from_db()
    assert presenca.status == 'presente'


@pytest.mark.django_db
def test_professor_registra_falta_justificada(client, professor_user, aluno, modalidade):
    """
    GIVEN uma aula agendada
    WHEN o professor valida a aula marcando um aluno como ausente com justificativa (sem mais nada no relatório)
    THEN o registro de presença deve ser salvo E o professor que validou deve ser registrado.
    """
    client.login(username='prof_teste', password='password123')
    aula = Aula.objects.create(
        modalidade=modalidade,
        data_hora=timezone.make_aware(timezone.datetime(2025, 9, 30, 15, 0)),
        status='Agendada'
    )
    aula.professores.set([professor_user])
    aula.alunos.set([aluno])
    # A view cria o objeto PresencaAluno, então não precisamos criar aqui.
    url = reverse('scheduler:aula_validar', kwargs={'pk': aula.pk})
    
    # Precisamos fazer um GET primeiro para a view criar os objetos de presença
    client.get(url)
    presenca = PresencaAluno.objects.get(aula=aula, aluno=aluno)

    form_data = {
        'presencas_alunos-TOTAL_FORMS': '1',
        'presencas_alunos-INITIAL_FORMS': '1',
        'presencas_alunos-0-id': presenca.id,
        'presencas_alunos-0-status': 'ausente',
        'presencas_alunos-0-tipo_falta': 'justificada',
        # Nenhum outro conteúdo de relatório é enviado
        'rudimentos-TOTAL_FORMS': '0', 'rudimentos-INITIAL_FORMS': '0',
        'ritmo-TOTAL_FORMS': '0', 'ritmo-INITIAL_FORMS': '0',
        'viradas-TOTAL_FORMS': '0', 'viradas-INITIAL_FORMS': '0',
    }
    
    client.post(url, data=form_data)
    
    # Verifica o status da presença
    presenca.refresh_from_db()
    assert presenca.status == 'ausente'
    assert presenca.tipo_falta == 'justificada'
    
    # Verifica o status da aula
    aula.refresh_from_db()
    assert aula.status == 'Aluno Ausente'

    # ★★★ NOVA VERIFICAÇÃO ★★★
    # Verifica se o professor que validou foi salvo no relatório
    relatorio = aula.relatorioaula
    assert relatorio.professor_que_validou == professor_user


@pytest.mark.django_db
def test_validar_aula_de_reposicao_muda_status_da_original(client, admin_user, aluno, modalidade):
    # Este teste já estava passando e continua correto. Nenhuma alteração necessária.
    client.login(username='admin_teste', password='password123')
    
    aula_original = Aula.objects.create(
        modalidade=modalidade, 
        data_hora=timezone.make_aware(timezone.datetime(2025, 10, 10, 10, 0)), 
        status='Aluno Ausente'
    )
    aula_original.alunos.set([aluno])

    aula_de_reposicao = Aula.objects.create(
        modalidade=modalidade, 
        data_hora=timezone.make_aware(timezone.datetime(2025, 10, 17, 10, 0)), 
        status='Agendada'
    )
    aula_de_reposicao.alunos.set([aluno])

    PresencaAluno.objects.create(
        aula=aula_original, 
        aluno=aluno, 
        status='ausente', 
        tipo_falta='justificada',
        aula_reposicao=aula_de_reposicao
    )
    
    url_validacao = reverse('scheduler:aula_validar', kwargs={'pk': aula_de_reposicao.pk})
    # Fazemos um GET para a view criar a presença
    client.get(url_validacao)
    presenca_reposicao = PresencaAluno.objects.get(aula=aula_de_reposicao, aluno=aluno)

    form_data = {
        'presencas_alunos-TOTAL_FORMS': '1',
        'presencas_alunos-INITIAL_FORMS': '1',
        'presencas_alunos-0-id': presenca_reposicao.id,
        'presencas_alunos-0-status': 'presente',
        'presencas_alunos-0-tipo_falta': 'injustificada',
        'conteudo_teorico': 'Aula de reposição realizada.',
        'rudimentos-TOTAL_FORMS': '0', 'rudimentos-INITIAL_FORMS': '0',
        'ritmo-TOTAL_FORMS': '0', 'ritmo-INITIAL_FORMS': '0',
        'viradas-TOTAL_FORMS': '0', 'viradas-INITIAL_FORMS': '0',
    }
    
    client.post(url_validacao, data=form_data)
    
    aula_original.refresh_from_db()
    assert aula_original.status == 'Reposta'