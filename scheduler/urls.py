from django.urls import path
from . import views

app_name = "scheduler"

urlpatterns = [
    # Página inicial/dashboard que será diferente para admin e professor
    path("", views.dashboard, name="dashboard"),
    path("horarios-fixos/", views.get_horario_fixo_data, name="get_horario_fixo_data"),
    path("get_calendario_html/", views.get_calendario_html, name="get_calendario_html"),
    path("api/marcar-tour-visto/", views.marcar_tour_visto, name="marcar_tour_visto"),
    # --- URLs para Gestão de Aulas ---
    path("aulas/", views.listar_aulas, name="aula_listar"),
    path("aula/agendar/", views.agendar_aula, name="aula_agendar"),
    path("aula/<int:pk>/validar/", views.validar_aula, name="aula_validar"),
    path("aula/<int:pk>/relatorio/", views.validar_aula, name="aula_relatorio"),
    path("aula/<int:pk>/editar/", views.editar_aula, name="aula_editar"),
    path("aula/<int:pk>/excluir/", views.excluir_aula, name="aula_excluir"),
    # URL para verificação de conflito via AJAX
    path(
        "aula/verificar_conflito/",
        views.verificar_conflito_aula,
        name="verificar_conflito_aula",
    ),
    # URL para exportação de aulas
    path("aulas/exportar/", views.exportar_aulas, name="exportar_aulas"),
    path(
        "relatorios/exportar/",
        views.exportar_relatorio_agregado,
        name="exportar_relatorio_agregado",
    ),
    # URL para obter horários ocupados via AJAX
    path(
        "aulas/get_horarios_ocupados/",
        views.get_horarios_ocupados,
        name="get_horarios_ocupados",
    ),
    # NOVO: URL para obter eventos do FullCalendar
    path(
        "aulas/eventos_calendario/",
        views.get_eventos_calendario,
        name="get_eventos_calendario",
    ),
    path(
        "aulas/substituir/", views.aulas_para_substituir, name="aulas_para_substituir"
    ),
    path("reposicoes/", views.listar_reposicoes_pendentes, name="reposicao_listar"),
    # --- URLs para Gestão de Alunos ---
    path("alunos/", views.listar_alunos, name="aluno_listar"),
    path("alunos/novo/", views.criar_aluno, name="aluno_criar"),
    path("alunos/<int:pk>/", views.detalhe_aluno, name="aluno_detalhe"),
    path("alunos/<int:pk>/editar/", views.editar_aluno, name="aluno_editar"),
    path("alunos/<int:pk>/excluir/", views.excluir_aluno, name="aluno_excluir"),
    # --- URLs para Gestão de Modalidades ---
    path("modalidades/", views.listar_modalidades, name="modalidade_listar"),
    path("modalidades/novo/", views.criar_modalidade, name="modalidade_criar"),
    path("modalidades/<int:pk>/", views.detalhe_modalidade, name="modalidade_detalhe"),
    path(
        "modalidades/<int:pk>/editar/",
        views.editar_modalidade,
        name="modalidade_editar",
    ),
    path(
        "modalidades/<int:pk>/excluir/",
        views.excluir_modalidade,
        name="modalidade_excluir",
    ),
    # --- URLs para Gestão de Professores ---
    path("colaboradores/", views.listar_professores, name="professor_listar"),
    path("colaborador/<int:pk>/", views.detalhe_professor, name="professor_detalhe"),
    path(
        "colaborador/<int:pk>/editar/", views.editar_professor, name="professor_editar"
    ),
    path(
        "colaborador/<int:pk>/excluir/",
        views.excluir_professor,
        name="professor_excluir",
    ),
    path(
        "professor/<int:pk>/filtrar-aulas/",
        views.filtrar_aulas_professor_ajax,
        name="filtrar_aulas_professor_ajax",
    ),
    # --- URLs para Relatórios ---
    path("relatorios/", views.relatorios_aulas, name="relatorios_aulas"),
    path("perfil/", views.perfil_usuario, name="perfil_usuario"),
    path('aluno/<int:aluno_id>/gerar-relatorio-ia/', views.gerar_relatorio_anual_ia, name='gerar_relatorio_ia'),
    path('relatorio/baixar-pdf/', views.baixar_relatorio_pdf, name='baixar_pdf'),
    path("normalizar-rudimentos/", views.normalizar_rudimentos, name="normalizar_rudimentos"),
]
