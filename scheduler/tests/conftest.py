import pytest
from scheduler.models import CustomUser, Aluno, Modalidade

@pytest.fixture
def professor_user(db):
    """Fixture para criar e retornar um usuário professor."""
    return CustomUser.objects.create_user(
        username='prof_teste', 
        password='password123', 
        tipo='professor'
    )

@pytest.fixture
def admin_user(db):
    """Fixture para criar e retornar um usuário admin."""
    return CustomUser.objects.create_user(
        username='admin_teste', 
        password='password123', 
        tipo='admin',
        is_staff=True,
        is_superuser=True
    )

@pytest.fixture
def aluno(db):
    """Fixture para criar e retornar um aluno."""
    return Aluno.objects.create(nome_completo='Aluno de Teste Pytest')

@pytest.fixture
def modalidade(db):
    """Fixture para criar e retornar uma modalidade."""
    return Modalidade.objects.create(nome='Bateria Pytest')