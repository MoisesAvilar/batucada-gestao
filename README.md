# Studio Batucada - Sistema de Gestão de Aulas de Música

Este é um sistema de gestão de aulas de música desenvolvido com Django (Python) no backend e HTML/CSS/JavaScript (Bootstrap 5, Flatpickr, FullCalendar) no frontend. Ele foi criado para otimizar o processo de agendamento, validação e visualização de aulas para administradores e professores.

## Sumário

* [Visão Geral](#visão-geral)
* [Funcionalidades Implementadas](#funcionalidades-implementadas)
* [Tecnologias Utilizadas](#tecnologias-utilizadas)
* [Configuração do Ambiente](#configuração-do-ambiente)
    * [Pré-requisitos](#pré-requisitos)
    * [Instalação](#instalação)
    * [Configuração do Banco de Dados](#configuração-do-banco-de-dados)
    * [Criação de Superusuário](#criação-de-superusuário)
    * [Configuração Google OAuth (Login Social)](#configuração-google-oauth-login-social)
* [Como Executar o Projeto](#como-executar-o-projeto)
* [Uso](#uso)
    * [Admin](#admin)
    * [Professor](#professor)
* [Melhorias Futuras (Sugestões)](#melhorias-futuras-sugestões)

## Visão Geral

O sistema "Studio Batucada - Gestão de Aulas de Música" centraliza o gerenciamento de alunos, professores, modalidades e aulas. Ele oferece interfaces intuitivas para agendamento, um fluxo flexível para substituições de professores e ferramentas visuais para acompanhamento da agenda.

## Funcionalidades Implementadas

1.  **Gestão de Alunos (CRUD):**
    * Listagem, criação, edição e exclusão de perfis de alunos.
    * Página de perfil detalhado por aluno, com histórico de todas as suas aulas.
2.  **Gestão de Modalidades (CRUD):**
    * Listagem, criação, edição e exclusão de modalidades de aula.
    * Validação que impede a exclusão de modalidades com aulas associadas.
3.  **Gestão de Professores (CRUD Parcial):**
    * Listagem, edição e exclusão de perfis de professores (que são usuários do sistema do tipo `CustomUser`). A criação é feita via admin Django ou conta social do Google.
    * Página de perfil detalhado por professor, com histórico de aulas atribuídas e aulas realmente ministradas (validadas).
    * Impedimento de autoexclusão para o administrador logado.
4.  **Agendamento de Aulas:**
    * Admin agenda aulas atribuindo aluno, professor, modalidade, data/hora e status inicial.
    * **Agendamento Recorrente:** Opção para agendar a mesma aula (mesmo professor, aluno, modalidade, horário) para todas as ocorrências do dia da semana escolhido no mês atual.
    * **Verificação de Conflito em Tempo Real (AJAX):** Ao selecionar professor e data/hora no formulário de agendamento/edição, o sistema verifica e informa visualmente se o professor já tem outra aula agendada naquele horário.
    * **Calendário Visual no Agendamento (Flatpickr):** O seletor de data/hora exibe os dias com aulas agendadas e desabilita horários específicos do professor selecionado.
5.  **Validação e Relatório de Aulas:**
    * Professores podem "validar" aulas (preencher um relatório detalhado de conteúdo ministrado, observações, etc.).
    * **Fluxo de Substituição:** Qualquer professor pode acessar a página de validação de *qualquer* aula agendada. Ao preencher e salvar o relatório, o sistema registra quem foi o `Professor que Realizou a Aula`, mantendo o `Professor Atribuído` original (se diferente).
    * Aulas realizadas exibem o relatório em modo de visualização.
6.  **Visualização de Aulas (Dashboard e Listagem):**
    * **Dashboard:**
        * Para **Admin**: Exibe todas as próximas aulas agendadas e um calendário visual (FullCalendar) com a agenda de todos os professores (com filtro opcional por professor).
        * Para **Professor**: Exibe um dashboard personalizado com "Minhas Próximas Aulas", "Aulas Pendentes de Validação" e "Minhas Últimas Aulas Realizadas".
        * Barra de busca (texto e intervalo de datas) e ordenação por colunas para a lista de aulas.
        * Paginação para a lista de aulas.
        * **Calendário FullCalendar:** Visão de agenda completa com eventos por status. É responsivo (visão de lista para mobile).
    * **Lista de Aulas (`/aulas/`):**
        * Para **Admin**: Exibe todas as aulas (histórico completo).
        * Para **Professor**: Exibe apenas as aulas que ele foi `Professor Atribuído` ou `Professor que Realizou`.
        * Ambos com busca, filtro e paginação.
    * **Realce Visual "Eu":** Linhas da tabela de aulas são visualmente destacadas para o professor logado quando a aula é atribuída a ele ou por ele realizada.
7.  **Relatórios Agregados:**
    * Página de relatórios para administradores com resumos de contagem de aulas por status, por professor e por modalidade, com filtros de data, professor, modalidade e status.
8.  **Exportação de Dados:**
    * Admin pode exportar a lista filtrada de aulas para um arquivo CSV, incluindo detalhes do relatório de aula.
9.  **Foto/Iniciais do Usuário Logado:**
    * Foto de perfil do Google é puxada via `django-allauth` e exibida no cabeçalho.
    * Para usuários sem foto de perfil (ou não Google), as iniciais do nome são exibidas em um avatar circular no cabeçalho.

## Tecnologias Utilizadas

* **Backend:**
    * Python 3.x
    * Django 5.x
    * SQLite (padrão para desenvolvimento)
* **Frontend:**
    * HTML5
    * CSS3 (Bootstrap 5.3.3)
    * JavaScript
    * Bootstrap Icons
    * Flatpickr (Date/Time Picker)
    * FullCalendar 6.x (Calendário Interativo)
* **Autenticação:**
    * `django.contrib.auth` (CustomUser)
    * `django-allauth` (Login Social com Google OAuth 2.0)

## Configuração do Ambiente

Siga estas instruções para configurar e rodar o projeto em sua máquina local.

### Pré-requisitos

* Python 3.8+ instalado
* `pip` (gerenciador de pacotes Python)

### Instalação

1.  **Clone o repositório:**
    ```bash
    git clone [URL_DO_SEU_REPOSITORIO]
    cd studio_gerenciamento
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv venv
    # No Windows:
    .\venv\Scripts\activate
    # No macOS/Linux:
    source venv/bin/activate
    ```

3.  **Instale as dependências Python:**
    ```bash
    pip install -r requirements.txt
    ```
    (Se você ainda não tem `requirements.txt`, pode gerá-lo com `pip freeze > requirements.txt` ou instalar manualmente: `pip install django django-allauth python-decouple` e outros que usar)

### Configuração do Banco de Dados

1.  **Execute as migrações do Django:**
    ```bash
    python manage.py makemigrations scheduler
    python manage.py migrate
    ```

### Criação de Superusuário

Crie uma conta de superusuário para acessar o painel de administração do Django e gerenciar os dados.

```bash
python manage.py createsuperuser