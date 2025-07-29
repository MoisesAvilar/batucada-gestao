# scheduler/tests/test_validacao.py

import pytest
from django.urls import reverse
from scheduler.models import Aula, RelatorioAula, PresencaAluno

@pytest.mark.django_db
def test_professor_valida_aula_com_sucesso(client, professor_user, aluno, modalidade):
    """
    GIVEN uma aula agendada atribuída a um professor
    WHEN o professor envia um POST com dados válidos de relatório e presença
    THEN a aula deve ter seu status mudado para 'Realizada'
    AND um RelatorioAula deve ser criado/atualizado com os dados corretos
    AND os registros de PresencaAluno devem ser atualizados.
    """
    # 1. ARRANGE (Preparação)
    # -----------------------
    # Faz o login como o professor
    client.login(username='prof_teste', password='password123')

    # Cria a aula agendada e associa o professor e o aluno
    aula = Aula.objects.create(
        modalidade=modalidade,
        data_hora='2025-08-05T10:00:00Z',
        status='Agendada'
    )
    aula.professores.set([professor_user])
    aula.alunos.set([aluno])

    # A view `validar_aula` cria os registros de presença na primeira visita (GET).
    # Aqui, criamos manualmente para simular que eles já existem para o formset.
    presenca = PresencaAluno.objects.create(aula=aula, aluno=aluno, status='presente')
    
    # URL para a qual vamos enviar os dados
    url = reverse('scheduler:aula_validar', kwargs={'pk': aula.pk})
    
    # Dados do formulário que seriam enviados pelo navegador
    report_data = {
        # Dados do formulário principal (RelatorioAulaForm)
        'conteudo_teorico': 'Estudamos a teoria das semicolcheias.',
        'observacoes_gerais': 'Ótimo desempenho do aluno.',
        
        # Dados do formset de presença (PresencaAlunoFormSet)
        'presencas_alunos-TOTAL_FORMS': '1',
        'presencas_alunos-INITIAL_FORMS': '1',
        'presencas_alunos-0-id': presenca.id, # ID do registro de presença que estamos editando
        'presencas_alunos-0-aula': aula.id,
        'presencas_alunos-0-aluno': aluno.id,
        'presencas_alunos-0-status': 'presente', # Marcando o aluno como presente

        # Dados dos formsets de exercícios (ItemRudimentoFormSet, etc.)
        # Enviamos os management forms mesmo que vazios.
        'rudimentos-TOTAL_FORMS': '1',
        'rudimentos-INITIAL_FORMS': '0',
        'rudimentos-0-descricao': 'Toque Simples', # Adicionando um item
        'rudimentos-0-bpm': '120',

        'ritmo-TOTAL_FORMS': '0',
        'ritmo-INITIAL_FORMS': '0',
        'viradas-TOTAL_FORMS': '0',
        'viradas-INITIAL_FORMS': '0',
    }

    # 2. ACT (Ação)
    # -------------
    # Envia a requisição POST para a view
    response = client.post(url, data=report_data)

    # 3. ASSERT (Verificação)
    # -----------------------
    # Verifica se a ação foi bem-sucedida e redirecionou para a lista de aulas
    assert response.status_code == 302, "A resposta deveria ser um redirecionamento"
    assert response.url == reverse('scheduler:aula_listar'), "Deveria redirecionar para a lista de aulas"

    # Recarrega a aula do banco de dados para pegar os dados atualizados
    aula.refresh_from_db()
    
    # Verifica se o status da aula foi atualizado corretamente
    assert aula.status == 'Realizada'

    # Verifica se o relatório foi salvo e associado corretamente
    assert hasattr(aula, 'relatorioaula'), "A aula deveria ter um relatório associado"
    relatorio = aula.relatorioaula
    assert relatorio.conteudo_teorico == 'Estudamos a teoria das semicolcheias.'
    assert relatorio.professor_que_validou == professor_user
    assert relatorio.itens_rudimentos.count() == 1
    assert relatorio.itens_rudimentos.first().descricao == 'Toque Simples'

    # Verifica se o status de presença do aluno foi salvo
    presenca.refresh_from_db()
    assert presenca.status == 'presente'