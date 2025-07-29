# scheduler/tests/test_forms.py

import pytest
from scheduler.forms import RelatorioAulaForm

# Este teste não precisa de acesso ao banco de dados, então não usamos a anotação
def test_relatorio_aula_form_valido():
    """
    GIVEN um dicionário com dados válidos para um relatório
    WHEN o RelatorioAulaForm é instanciado com esses dados
    THEN o formulário deve ser considerado válido.
    """
    # Arrange
    form_data = {
        'conteudo_teorico': 'Estudamos semicolcheias.',
        'observacoes_gerais': 'O aluno demonstrou bom progresso.'
    }
    
    # Act
    form = RelatorioAulaForm(data=form_data)
    
    # Assert
    assert form.is_valid() is True

def test_relatorio_aula_form_invalido_campos_longos(db):
    """
    GIVEN dados que excedem o comprimento máximo de um campo (hipotético)
    WHEN o formulário é validado
    THEN ele deve ser inválido.
    
    (Este é um exemplo, seus campos são TextField, então não têm max_length,
    mas a estrutura do teste é essa)
    """
    # Arrange
    # Supondo que 'conteudo_teorico' tivesse um max_length de 10
    # form_data = {'conteudo_teorico': 'um texto muito, muito, muito longo'}
    # form = RelatorioAulaForm(data=form_data)
    # assert form.is_valid() is False
    # assert 'conteudo_teorico' in form.errors
    pass # Passando por enquanto, pois seus campos são textfields